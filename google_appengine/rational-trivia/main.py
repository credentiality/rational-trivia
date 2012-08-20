import cgi
import datetime
import urllib
import webapp2
import glob
import logging
import random
import uuid
import jinja2
import os
import math

from webapp2_extras import sessions

from google.appengine.ext import db
from google.appengine.api import users

jinja_environment = jinja2.Environment(
  loader=jinja2.FileSystemLoader(os.path.dirname(__file__)))


class User(db.Model):
  pseudonym = db.StringProperty()
  correct_answers = db.IntegerProperty()
  total_answers = db.IntegerProperty()

class MultipleChoiceQuestion(object):
  def __init__(self, uuid, q, a1, a2, a3, a4, answer):
    self.uuid_ = uuid
    self.q_ = q
    self.a1_ = a1
    self.a2_ = a2
    self.a3_ = a3
    self.a4_ = a4
    self.answer_ = answer

  def uuid(self):
    return self.uuid_

  def answers(self):
    return [self.a1_, self.a2_, self.a3_, self.a4_]

  def answer(self):
    return self.answer_

  def question(self):
    return self.q_

class Questions(object):
  def __init__(self):
    self.num_questions = 0
    self.questions = []
    self.read_questions()

  def read_questions(self):
    files = glob.glob("misterhouse/*.dat.txt")
    for fn in files:
      f = open(fn, "r")
      for line in f:
        line = line.rstrip("\n")
        fields = line.split('|')

        q = MultipleChoiceQuestion(self.num_questions,
                                   fields[0],
                                   fields[1],
                                   fields[2],
                                   fields[3],
                                   fields[4],
                                   fields[5])

        self.questions.append(q)
        self.num_questions += 1
    logging.info("Read " + str(self.num_questions) + " questions.")

  def random_question(self):
    index = random.randint(0, self.num_questions - 1)
    return self.questions[index]


class MainPage(webapp2.RequestHandler):
  def dispatch(self):
    self.session_store = sessions.get_store(request=self.request)
    try:
      webapp2.RequestHandler.dispatch(self)
    finally:
      self.session_store.save_sessions(self.response)

  @webapp2.cached_property
  def session(self):
    return self.session_store.get_session()

  def session_reset(self):
    self.session['total_questions'] = 0
    self.session['correct_questions'] = 0
    self.session['confidence_error'] = 0

  # First time users get caught here.
  def session_check(self):
    if ((self.session.get('total_questions') is None) or
        (self.session.get('correct_questions') is None) or
        (self.session.get('confidence_error') is None)):
         session_reset()

  def post(self):
    if self.request.get('reset_stats') == "true":
      self.session_reset()
      self.redirect('/')
      return

    # Get the form values
    answer = self.request.get('answer')
    confidence = float(self.request.get('confidence'))
    uuid = self.request.get('question_uuid')
    correct_answer = self.request.get('correct_answer')

    logging.debug("answer:%s/%s confidence:%s uuid:%s", answer,
                  correct_answer, confidence, uuid)

    self.session_check()

    total_questions = self.session.get('total_questions')
    total_questions += 1
    self.session['total_questions'] = total_questions

    # FANCIER MATH GOES HERE

    # Calculates our confidence error for just this question
    was_correct = False
    absolute_error = 1.0  # prediction vs. reality for this question
    if answer == correct_answer:
      was_correct = True
      absolute_error = math.fabs(100 - confidence)
    else:
      absolute_error = math.fabs(0 - confidence)

    # Sums total correct questions for all time
    correct_questions = self.session.get('correct_questions')
    if was_correct:
      correct_questions += 1
    self.session['correct_questions'] = correct_questions

    # Calculates overall confidence error for all time
    confidence_error = self.session.get('confidence_error')
    confidence_error = \
      (confidence_error*(total_questions-1) + absolute_error) / total_questions
    self.session['confidence_error'] = confidence_error

    # Calculates correctness rate for all time
    self.session['correctness'] = 1.0 * correct_questions / total_questions

    self.redirect('/')

  def get(self):
    q = questions.random_question()

    self.session_check()

    template_values = {
        # User stats:
        'confidence_error': round(self.session.get('confidence_error')),
        'correctness': int(100 * self.session.get('correctness')),
        'correct_questions': self.session.get('correct_questions'),
        'total_questions': self.session.get('total_questions'),

        # The next question:
        'question': q.question(),
        'answers': q.answers(),
        'correct_answer': q.answer(),
        'uuid': q.uuid(),
    }

    template = jinja_environment.get_template('index.html')
    self.response.out.write(template.render(template_values))

questions = Questions()

session_secret = {}
session_secret['webapp2_extras.sessions'] = {
  'secret_key': 'my-super-secret-key',
}

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/post', MainPage),],
                              debug=True,
                              config=session_secret)
