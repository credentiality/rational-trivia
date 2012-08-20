#!/usr/bin/perl
#

open (INDATA, "< $ARGV[0]") or die "Error, could not open";

my $r;
read (INDATA, $r, 30);
my $category = substr($r, 0, 20);

while (read(INDATA, $r, 153)) {
  my $q = substr($r, 0, 70);
  my @a;
  $a[1] = substr($r,  72, 20);
  $a[2] = substr($r,  92, 20);
  $a[3] = substr($r, 112, 20);
  $a[4] = substr($r, 132, 20);
  my $an= substr($r, 152, 1);

  $out = join('|', $q, @a[1..4], $an);
  $out =~ s/\s+/ /g;
  print $out, "\n";
}


