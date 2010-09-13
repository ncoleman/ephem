#!/home/nickcoleman/local/bin/python
#coding=utf-8

import cgi, cgitb
import os
import Cookie

def main():
    day = 0
    month = 0
    year = 0

    print """Content-Type: text/html\n\n
            <html><head>
            <link rel=\"stylesheet\" href=\"/blog/kukka.css\" type=\"text/css\" />
            </head><body><div="content1"><div="content2"><div="content3"><div="post">
            """

    form = cgi.FieldStorage()
    print "form", form
    if form.getvalue('processed'):
        print "form keys", form.keys()
        day, month, year = form.getvalue('day'), form.getvalue('month'), form.getvalue('year')
        print day, month, year 

    print """
        <form action="/ephem/hello.py" method="POST">"""
    print "<fieldset><legend><b>Date & Time</b></legend>"
    print 'Day: <input type="text" name="day" value="" size="5" />' #% day
    print 'Month: <input type="text" name="month" value="%s" size="5" />' % month 
    print 'Year: <input type="text" name="year" value="%s" size="5" /><br />' % year
    print """</fieldset>
        <fieldset><legend><b>Go</b></legend>
        <input type="hidden" name="processed" value="True" />
        <input type="submit" value="Submit" />
        </fieldset>
        </form>"""

    print "</body></html>"

if __name__ == '__main__':
    main()
