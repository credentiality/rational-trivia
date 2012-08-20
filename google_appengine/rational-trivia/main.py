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
  def __init__(self, guid, q, a1, a2, a3, a4, answer):
    self.guid = guid
    self.q = q
    self.a1 = a1
    self.a2 = a2
    self.a3 = a3
    self.a4 = a4
    self.answer = answer

  def guid(self):
    return self.guid

  def answers(self):
    return [self.a1, self.a2, self.a3, self.a4]

  def answer(self):
    return self.answer

  def question(self):
    return self.q

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

  def get(self):

    template_values = {
        'foo': "foo"
    }

    template = jinja_environment.get_template('index.html')
    self.response.out.write(template.render(template_values))

    return

    foo = self.session.get('bar')

    logging.info("foo=" + str(foo))

    self.response.out.write('<html><body>')

    q = questions.random_question()
    self.response.out.write("Question: " + q.question())

    return

    guestbook_name=self.request.get('guestbook_name')

    # Ancestor Queries, as shown here, are strongly consistent with the High
    # Replication Datastore. Queries that span entity groups are eventually
    # consistent. If we omitted the ancestor from this query there would be a
    # slight chance that Greeting that had just been written would not show up
    # in a query.
    greetings = db.GqlQuery("SELECT * "
                            "FROM Greeting "
                            "WHERE ANCESTOR IS :1 "
                            "ORDER BY date DESC LIMIT 10",
                            guestbook_key(guestbook_name))

    for greeting in greetings:
      if greeting.author:
        self.response.out.write(
            '<b>%s</b> wrote:' % greeting.author)
      else:
        self.response.out.write('An anonymous person wrote:')
      self.response.out.write('<blockquote>%s</blockquote>' %
                              cgi.escape(greeting.content))

    self.response.out.write("""
          <form action="/sign?%s" method="post">
            <div><textarea name="content" rows="3" cols="60"></textarea></div>
            <div><input type="submit" value="Sign Guestbook"></div>
          </form>
          <hr>
          <form>Guestbook name: <input value="%s" name="guestbook_name">
          <input type="submit" value="switch"></form>
        </body>
      </html>""" % (urllib.urlencode({'guestbook_name': guestbook_name}),
                          cgi.escape(guestbook_name)))


class Guestbook(webapp2.RequestHandler):
  def post(self):
    # We set the same parent key on the 'Greeting' to ensure each greeting is in
    # the same entity group. Queries across the single entity group will be
    # consistent. However, the write rate to a single entity group should
    # be limited to ~1/second.
    guestbook_name = self.request.get('guestbook_name')
    greeting = Greeting(parent=guestbook_key(guestbook_name))

    if users.get_current_user():
      greeting.author = users.get_current_user().nickname()

    greeting.content = self.request.get('content')
    greeting.put()
    self.redirect('/?' + urllib.urlencode({'guestbook_name': guestbook_name}))


questions = Questions()

session_secret = {}
session_secret['webapp2_extras.sessions'] = {
  'secret_key': 'my-super-secret-key',
}

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/sign', Guestbook)],
                              debug=True,
                              config=session_secret)
