#!/home/nickcoleman/local/bin/python -Wignore::DeprecationWarning
#coding=utf-8
#!/usr/bin/env python -Wignore::DeprecationWarning
#!/usr/bin/python -Wignore::DeprecationWarning
#!/home/nickcoleman/local/bin/python -Wignore::DeprecationWarning

from __future__ import with_statement
import cgi, cgitb
import os
import re
import Cookie
from datetime import datetime
import ephem
import pytz

#   config variables
messierdb = 'Messier.edb'
tlefile = 'visual.txt'
tleurl = 'www.celestrak.com/NORAD/elements/'
# end config

# params notes:  
# date and time are stored as entered by user, 
# utc_date tuple is that converted to UTC; 
# utc is boolean indicating whether user is using UTC or local. 
# now is used to indicate whether to override the date with the current time.
# save indicates whether to save settings with cookies

# Booleans: processed, now, save, utc, save, altaz

# Cookies: save, utc, now, minute, hour, day, month, year, city, lat, long, tzname, elev
params = {
    'processed' : False,
    'now' : False,
    'save' : False,
    'second': 0.0,          # to resolve rounding errors in the Date float
    'minute' : None,
    'hour' : None,
    'day' : None,
    'month' : None,
    'year' : None,
    'utc_date' : (),
    'utc' : False,
    'tzname': None,
    'city' : None,
    'lat' : None,
    'long' : None,
    'elev' : None,
    'temp' : None, 
    'pressure' : None,
    'star' : [],
    'messier' : [],
    'body' : None,
    'sun' : None,
    'moon' : None,
    'mercury' : None,
    'venus' : None,
    'mars' : None,
    'jupiter' : None,
    'saturn' : None,
    'uranus': None,
    'neptune': None,
    'altaz' : True,
    'above_horiz' : False,
    'minmag' : None
}

booleans = ('processed', 'now', 'utc', 'save', 'altaz', 'above_horiz')

def main():
    cgitb.enable()
    valid = True
    validMsg = ''
    tick = datetime.now()
    # There are three initial states:
    #   no cookies, where everything must be initialised to default values
    #   cookies, where time, location must be set and missing values set to default, and the rest initialised
    #   POST, where everything has already been initialised and now changed, then calc'ed and cookies set.
    # Workflow
    # Initialise:
    #   get values:
    #       if from POST
    #       elif from cookies
    #       else from defaults
    # Then:
    #   perform calcs
    #   display:
    #       display headers
    #           set cookies
    #       display form
    #       display results
    #       display footers

    # Do setup for POST and cookies
    form = cgi.FieldStorage()
    cookie = Cookie.SimpleCookie()
    try:
        cookie.load(os.environ['HTTP_COOKIE'])
    except KeyError:                                # no HTTP_COOKIE
        pass

    # do POST processing
    #if form.has_key('processed'):                   # then this is the result of a POST
    if 'processed' in form:
        for key in form:
            params[key] = form.getvalue(key)
        params['star'] = form.getlist('star')                 # except that star is a special case
        params['messier'] = form.getlist('messier')                 # except that messier is a special case
        if form.has_key('clear'):
            setCookies(clear=True)
        
    # do cookies processing
    elif cookie.has_key('save'):
        for key in cookie.keys():
            if params.has_key(key):                             # skip unknown cookies (perhaps set by server)
                value = cookie[key].value
                if value and value is not "None" and value is not "False":
                    params[key] = cookie[key].value
        #params['processed'] = True
    # set defaults if not already set
    else:
        params['year'], params['month'], params['day'], params['hour'], params['minute']  = datetime.utcnow().timetuple()[:5]
        params['utc'] = True
        params['tzname'] = 'UTC'
    #  fill in any blanks
    _date = datetime.utcnow().timetuple()[:5]
    i = 0
    for key in ('year', 'month', 'day', 'hour', 'minute'):
        if not params[key]:
            params[key] = _date[i]
        i += 1

    # perform validation and tidying
    # validation still needed since user may have edited cookies externally,
    # so I moved validation outside of form processing and now it is done for everything.

    # tidy up the booleans
    for key in booleans:
        value = params[key]
        if value in ('True', 'UTC', 'now'):
            params[key] = True
        if value in ('None', '', 'False'):
            params[key] = False
    # tidy up the floats
    for key in ('elev', 'temp', 'pressure', 'minmag'):
        try:                                        # if it can be made a float,
            params[key] = float(params[key])        # do it
        except:
            pass                                    # else, don't do it.
    
    # do form processing
    if params['processed']:
        for key in ('minute', 'hour', 'day', 'month'):
            params[key] = int(params[key])          # tidy up params to correct type; has to be before validation so strings are ints (not year though)

        # do validation
        valid, validMsg = validateParams()

        if valid:
            # do calcs
            if params['now']:
                _date = datetime.utcnow().timetuple()[:5]
                if params['utc']:
                    params['year'], params['month'], params['day'], params['hour'], params['minute'] = _date
                else:
                    params['year'], params['month'], params['day'], params['hour'], params['minute'] = getLocalDateTime(_date)[:5]

            params['year'] = int(params['year'])          # tidy up params to correct type
            setUTCDate()
            for key in ('temp', 'pressure', 'elev', 'minmag'):
                try:
                    if params[key]:      # tidy to correct type *if it exists*
                        params[key] = float(params[key])
                except ValueError:
                    pass
            # do ephem stuff
            home = doEphemStuff()
            setCookies()

    print "Content-Type: text/html; charset=utf-8\n\n"
    renderHTMLHead()
    if not valid:
        renderErrors(validMsg)
    print '<div id="forms">'
    renderForm()
    print '<div id="output">'
    print "<p><b>Results:</b></p>"

    # render output
    if params['processed'] and valid:
        print '<p>Times are %s except where specified.</p>' % (params['utc'] and 'UTC' or 'local for ' + params['tzname'])
        try:
            print "<p>For time:  <br />%s Local <br />%s UTC <br />Timezone: %s<br /></p><p>Location:  %s, lat %s long %s<br />Parameters: temperature %sC, elevation %4.0f metres, barometer %4.0f mBar.</p>" % (datetime(*getLocalDateTime(home.date.tuple())[:6]).strftime("%F %R"),  home.date.datetime().strftime("%F %R"), params['tzname'], home.name, home.lat, home.long, home.temp, home.elev, home.pressure)
        except ValueError:
            # datetime.strftime can't be earlier than 1900, raises ValueError. I prefer the output for strftime, so use it
            # whenever possible, but handle the exceptional case as well by not using strftime then.
            print "<p>For time:  <br />%s Local <br />%s UTC <br />Timezone: %s<br /></p><p>Location:  %s, lat %s long %s<br />Parameters: temperature %sC, elevation %4.0f metres, barometer %4.0f mBar.</p>" % (datetime(*getLocalDateTime(home.date.tuple())[:6]),  home.date.datetime(), params['tzname'], home.name, home.lat, home.long, home.temp, home.elev, home.pressure)
        print "<p>Local noon: %02d:%02d:%02d</p>" % getLocalDateTime(params['sun'].transit_time.tuple())[3:6]
        previous_vernal = ephem.previous_vernal_equinox(home.date).tuple()
        previous_autumnal = ephem.previous_autumnal_equinox(home.date).tuple()
        previous_summer = ephem.previous_summer_solstice(home.date).tuple()
        previous_winter = ephem.previous_winter_solstice(home.date).tuple()
        next_vernal = ephem.next_vernal_equinox(home.date).tuple()
        next_autumnal = ephem.next_autumnal_equinox(home.date).tuple()
        next_summer = ephem.next_summer_solstice(home.date).tuple()
        next_winter = ephem.next_winter_solstice(home.date).tuple()
        if not params['utc']:
            previous_vernal = getLocalDateTime(previous_vernal)
            previous_autumnal = getLocalDateTime(previous_autumnal)
            previous_summer = getLocalDateTime(previous_summer)
            previous_winter = getLocalDateTime(previous_winter)
            next_vernal = getLocalDateTime(next_vernal)
            next_autumnal = getLocalDateTime(next_autumnal)
            next_summer = getLocalDateTime(next_summer)
            next_winter = getLocalDateTime(next_winter)
        print """<table cellpadding=\"5\" cellspacing=\"5\" class=\"seasons\" >
            <tr><tr><th class=\"seasons\">Seasons</th></tr>
            <tr><td>Previous</td>
            <td>Equinoxes:</td><td>%d-%02d-%02d %02d:%02d</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td></td><td>Solstices:</td><td>%d-%02d-%02d %02d:%02d</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td>Next</td>
            <td>Equinoxes:</td><td>%d-%02d-%02d %02d:%02d</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td></td><td>Solstices:</td><td>%d-%02d-%02d %02d:%02d</td><td>%d-%02d-%02d %02d:%02d</td></tr></table>
            """ % (
                    previous_vernal[:5] + previous_autumnal[:5] + previous_summer[:5] + previous_winter[:5] +
                    next_vernal[:5] + next_autumnal[:5] + next_summer[:5] + next_winter[:5])
        next_full_moon = ephem.next_full_moon(home.date).tuple()
        next_new_moon = ephem.next_new_moon(home.date).tuple()
        next_crescent_moon = getCrescentMoon(home, next_new_moon).tuple()
        prev_full_moon = ephem.previous_full_moon(home.date).tuple()
        prev_new_moon = ephem.previous_new_moon(home.date).tuple()
        prev_crescent_moon = getCrescentMoon(home, prev_new_moon).tuple()
        if not params['utc']:
            next_full_moon = getLocalDateTime(next_full_moon)
            next_new_moon = getLocalDateTime(next_new_moon)
            next_crescent_moon = getLocalDateTime(next_crescent_moon)
            prev_full_moon = getLocalDateTime(prev_full_moon)
            prev_new_moon = getLocalDateTime(prev_new_moon)
            prev_crescent_moon = getLocalDateTime(prev_crescent_moon)
        moons = {next_new_moon[:6]: 'New', next_full_moon[:6]: 'Full', next_crescent_moon[:6]: 'Crescent',
                prev_new_moon[:6]: 'New', prev_full_moon[:6]: 'Full', prev_crescent_moon[:6]: 'Crescent' }
        moon_keys = moons.keys()            # keys are ephem dates in tuple format when printed
        moon_keys.sort()                    # NB sort works correctly on tuples !
        print """<table cellpadding=\"5\" cellspacing=\"5\" class=\"seasons\" >
            <tr><th class=\"seasons\">Moon</th></tr>
            <tr><td>Previous</td><td>%s:</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td></td><td>%s:</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td></td><td>%s:</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td>Next</td><td>%s:</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td></td><td>%s:</td><td>%d-%02d-%02d %02d:%02d</td></tr>
            <tr><td></td><td>%s:</td><td>%d-%02d-%02d %02d:%02d</td></tr></table>""" % (
            moons[moon_keys[0]], moon_keys[0][0], moon_keys[0][1], moon_keys[0][2], moon_keys[0][3], moon_keys[0][4], 
            moons[moon_keys[1]], moon_keys[1][0], moon_keys[1][1], moon_keys[1][2], moon_keys[1][3], moon_keys[1][4], 
            moons[moon_keys[2]], moon_keys[2][0], moon_keys[2][1], moon_keys[2][2], moon_keys[2][3], moon_keys[2][4],
            moons[moon_keys[3]], moon_keys[3][0], moon_keys[3][1], moon_keys[3][2], moon_keys[3][3], moon_keys[3][4], 
            moons[moon_keys[4]], moon_keys[4][0], moon_keys[4][1], moon_keys[4][2], moon_keys[4][3], moon_keys[4][4],
            moons[moon_keys[5]], moon_keys[5][0], moon_keys[5][1], moon_keys[5][2], moon_keys[5][3], moon_keys[5][4])
        altaz = params['altaz'] and ('Altitude', 'Azimuth') or ('RA', 'Dec')
        print '<p><small>Times are %s. Click column heading to sort.</small></p>' % (params['utc'] and 'UTC' or 'local')
        print '<table class="sortable" id="results_bodies" ><tr><th>Body</th><th>%s</th><th>%s</th><th>Dir</th><th>Const</th><th>Mag</th><th>Phase</th><th>Rise</th><th>Set</th><th>TransAlt</th></tr>' % (altaz)
        print_fmt = '<tr><td>%s</td><td>%s</td><td>%3s</td><td>%3s</td><td>%3s</td><td>%.0f</td><td>%.0f</td><td>%s</td><td>%s</td><td>%s</td></tr>'
        # For all three sections: body, star and messier, the second compute is needed because home.next_(setting|rising) sets the body's
        # compute date to that time, meaning any subsequesnt alt/az display is incorrect.  Recompute to calculate correct settings.
        for body in ('sun','moon','mercury','venus','mars','jupiter','saturn','uranus','neptune'):
            params[body].compute(home)
            if params['above_horiz'] and params[body].alt < 0:
                continue
            rtime,stime = getNextRiseSet(params[body], home)
            if not params['utc']:
                rtime = getLocalDateTime(rtime)
                stime = getLocalDateTime(stime)
            risetime = '%02.0f:%02.0f' % (rtime[3], rtime[4])
            settime = '%02.0f:%02.0f' % (stime[3], stime[4])
            params[body].compute(home)
            altazradec = params['altaz'] and (params[body].alt, params[body].az) or (params[body].ra, params[body].dec)
            print print_fmt % (body.capitalize(), roundAngle(altazradec[0]), roundAngle(altazradec[1]), azDirection(params[body].az), ephem.constellation(params[body])[1][:6], params[body].mag, params[body].phase, risetime, settime, roundAngle(params[body].transit_alt))
        print """</table>"""

        print '<table class="sortable" id="results_stars" ><tr><th>Star</th><th>%s</th><th>%s</th><th>Dir</th><th>Const</th><th>Mag</th><th>Rise</th><th>Set</th><th>TransAlt</th></tr>' % altaz
        stars = []
        for s in params['star']:
            stars.append(ephem.star(s))
        for s in stars:
            s.compute(home)
            if params['above_horiz'] and s.alt < 0:                                   # only bother if star is above the horizon 
                continue
            if params['minmag'] and s.mag > params['minmag']:                       # only bother if star is brighter than ( < ) X
                continue
            rtime,stime = getNextRiseSet(s, home)
            if rtime[0] == -1 or stime[0] == -1:
                # don't want to do any formatting
                risetime = -1
                settime = -1
            else:
                if not params['utc']:
                    rtime = getLocalDateTime(rtime)
                    stime = getLocalDateTime(stime)
                risetime = '%02.0f:%02.0f' % (rtime[3], rtime[4])
                settime = '%02.0f:%02.0f' % (stime[3], stime[4])
            s.compute(home)
            #print '<p>%s, az %s, alt %s, mag %2.0f</p>' % (s.name, roundAngle(s.az), roundAngle(s.alt), s.mag)
            altazradec = params['altaz'] and (s.alt, s.az) or (s.ra, s.dec)
            print_fmt = '<tr><td>%s</td><td>%s</td><td>%3s</td><td>%3s</td><td>%3s</td><td>%.0f</td><td>%s</td><td>%s</td><td>%s</td></tr>'
            print print_fmt % (s.name, roundAngle(altazradec[0]), roundAngle(altazradec[1]), azDirection(s.az), ephem.constellation(s)[1][:6], s.mag, risetime, settime, roundAngle(s.transit_alt))
        print '</table>'

        print '<table class="sortable" id="results_messiers" ><tr><th>Messier</th><th>%s</th><th>%s</th><th>Dir</th><th>Const</th><th>Mag</th><th>Rise</th><th>Set</th><th>TransAlt</th></tr>' % altaz
        messiers = []
        for m in params['messier']:
            messiers.append(ephem.readdb(getMessierEdb(m.split()[0])))
        for m in messiers:
            m.compute(home)
            if params['above_horiz'] and m.alt < 0:                                   # only bother if star is above the horizon 
                continue
            if params['minmag'] and m.mag > params['minmag']:
                continue
            rtime,stime = getNextRiseSet(m, home)
            if rtime[0] == -1 or stime[0] == -1:
                # don't want to do any formatting
                risetime = -1
                settime = -1
            else:
                if not params['utc']:
                    rtime = getLocalDateTime(rtime)
                    stime = getLocalDateTime(stime)
                risetime = '%02.0f:%02.0f' % (rtime[3], rtime[4])
                settime = '%02.0f:%02.0f' % (stime[3], stime[4])
            m.compute(home)
            #print '<p>%s, az %s, alt %s, mag %2.0f</p>' % (m.name, roundAngle(m.az), roundAngle(m.alt), m.mag)
            altazradec = params['altaz'] and (m.alt, m.az) or (m.ra, m.dec)
            print_fmt = '<tr><td>%s</td><td>%s</td><td>%3s</td><td>%3s</td><td>%3s</td><td>%.0f</td><td>%s</td><td>%s</td><td>%s</td></tr>'
            print print_fmt % (m.name, roundAngle(altazradec[0]), roundAngle(altazradec[1]), azDirection(m.az), ephem.constellation(m)[1][:6], float(m.mag), risetime, settime, roundAngle(m.transit_alt))
        print '</table>'
            
        tock = datetime.now()
        print "<p><small>Done in %s.</small></p>" % ( tock - tick)
    print """</div><!-- output -->
            </div><!-- forms -->"""
    renderHTMLIntro()
    renderHTMLFooter()

def doEphemStuff():
    """ creates home and planets; returns home"""
    if params['city']:
        params['lat'], params['long'] = None, None
        home = ephem.city(params['city'])
    elif params['lat'] and params['long']:
        home = ephem.Observer()
        home.name = 'provided input'
        home.lat = params['lat']
        home.long = params['long']
        home.temp = 15.0        # will be overridden below if a value was manually entered
        home.elev = 0.0
        home.pressure = 1010.0
    else:
        params['city'] = 'London'
        home = ephem.city(params['city'])
    if params['temp']:
        home.temp = params['temp']
    if params['elev']:
        home.elev = params['elev']
    if params['pressure']:
        home.pressure = params['pressure']
    home.date = ephem.Date(params['utc_date'])
    params['sun'] = ephem.Sun(home)
    params['moon'] = ephem.Moon(home)
    params['mercury'] = ephem.Mercury(home)
    params['venus'] = ephem.Venus(home)
    params['mars'] = ephem.Mars(home)
    params['jupiter'] = ephem.Jupiter(home)
    params['saturn'] = ephem.Saturn(home)
    params['uranus'] = ephem.Uranus(home)
    params['neptune'] = ephem.Neptune(home)
    return home



def roundAngle(angle):
    """ return the integer degrees part of the string representation of an angle"""
    # an alternative is some sort of variant of str(angle)[:2].  The problem is that the first few digits is variable, so splitting on ":" is better for all cases.
    return str(angle).split(":")[0]


def azDirection(az):
    """ return the direction (North, South, North-East etc, shown as N, S, NE) for an azimuth"""
    quadrant = int(round(az*180/ephem.pi/45.0))
    return {0:'N', 1:'NE', 2:'E',3:'SE',4:'S',5:'SW',6:'W',7:'NW',8:'N'}[quadrant]


def renderHTMLHead():
    #print """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd">
    print """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" 
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
    <html  xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
        <head>
            <meta http-equiv="Content-Type" content="text/html;charset=utf-8" />
            <meta name="keywords" content="ephemeris, online, online epheris, xephem, python, pyephem" />
            <meta name="description" content="web based online ephemeris written in Python using the pyephem module" />
            <link rel="stylesheet" href="ephemeris.css" type="text/css" />
            <link rel="shortcut icon" href="favicon.ico" />
            <script type="text/javascript" src="js/sortable.js"></script>
            <title>Online Ephemeris</title>
        </head>
        <body><div id="content">Back to <a name="top"></a><a href="/">Home</a><h1>Ephemeris</h1><p><a href="#intro"><h3>Features &amp; Help</h3></a></p>"""


def renderHTMLFooter():
    print """</div><!-- content -->
        <script type="text/javascript">
            function uncheckNow() {
                var elements = document.getElementsByName('now');
                elements[0].checked = false;        // poss Bug: assumes only one element named 'now'
            }

            function uncheckLocation(){
                document.getElementsByName('lat')[0].value = ""
                document.getElementsByName('long')[0].value = ""
                document.getElementsByName('elev')[0].value = ""
                document.getElementsByName('temp')[0].value = ""
                document.getElementsByName('pressure')[0].value = ""
            }

            function uncheckCity(){
                document.getElementsByName('city')[0].value = ""
            }

        </script>
        <script type="text/javascript"> 
        <!--
            document.write('<img src="/axs/ax.pl?mode=img&ref=');
            document.write( escape( document.referrer ) );
            document.write('" height="1" width="1" style="display:none" alt="" />');
        // -->
        </script><noscript> 
            <img src="/axs/ax.pl?mode=img" height="1" width="1" style="display:none" alt="" /> 
        </noscript> 
        </body></html>"""


def getCookies():
    cookie = Cookie.SimpleCookie()
    cookie.load(os.environ['HTTP_COOKIE'])
    for key in cookie.keys():
        params['key'] = cookie[key].value

def setCookies(clear=False):
    cookie = Cookie.SimpleCookie()
    if clear:
        expire = -1                                  # 
    else:
        expire = 63072000                           # 2 years in seconds
    for key in ('hour', 'minute', 'day', 'month', 'year', 'now', 'utc', 'tzname', 'city', 'lat', 'long', 'elev', 'save'): 
        cookie[key] = params[key]
        cookie[key]['path'] = '/ephem'
        if params[key]:                             # avoid None or False params
            cookie[key]['expires'] = expire
        else:                                       # the purpose of this is to expire existing cookie where the value has been changed to None or False
            cookie[key]['expires'] = -1
    if params['save'] or clear:
        print cookie.output()


def validateParams():
    validType = validateMsgType = True
    validRelationship = validateMsgRelationship = ''
    def validateTypes():
        valid = True
        validateMsg = ''
        # 00:00:00 or 00.0000
        if params['lat'] and not re.match(r'^[+-]?([0-9]{1,3}(:[0-9]{1,3})+)|([0-9]*.[0-9]*)$',params['lat']):
            validateMsg += r'<p class="error">Latitude invalid.</p>'
            valid = False
        if params['long'] and not re.match(r'^[-+]?([0-9]{1,3}(:[0-9]{1,3})+)|([0-9]*.[0-9]*)$',params['long']):
            validateMsg += r'<p class="error">Longitute invalid.</p>'
            valid = False
        # -/+ any 3 digit number plus floating part
        if params['temp'] and not re.match(r'^[-+]?[0-9]{1,3}(\.[0-9]*)*$', str(params['temp'])):
            validateMsg += r'<p class="error">Temperature %s is invalid</p>' % params['temp']
            valid = False
        # any positive 4 digit number plus floating part
        if params['elev'] and not re.match(r'^[-+]?[0-9]{1,4}(\.[0-9]*)*$', str(params['elev'])):
            validateMsg += r'<p class="error">Elevation %s is invalid</p>' % params['elev']
            #params['elev'] = 0.0
            valid = False
        if params['pressure'] and not re.match(r'^0|([0-9]{3,4}(\.[0-9]*)?)$', str(params['pressure'])):
            validateMsg += r'<p class="error">Pressure %s is invalid</p>' % params['pressure']
            valid = False
        if params['year']:
            try:                                            # workaround for annoying bug when year is empty and re module raises exception.
                if not re.match(r'^([1-9]{1}|[0-9]{2,4})$', params['year']):
                    validateMsg += r'<p class="error">Year %s is invalid</p>' % params['year']
                    valid = False
            except TypeError:
                validateMsg += r'<p class="error">Year was invalid, current year substituted. Re-submit.</p>'
                valid = False
        else:
            validateMsg += r'<p class="error">Year is invalid</p>'
            valid = False
        if params['minmag'] and not re.match(r'^[+-]?[0-9]{1,2}(\.[0-9]*)*$', str(params['minmag'])):
            validateMsg += r'<p class="error">Brighter than magnitude %s is invalid</p>' % params['minmag']
        return valid, validateMsg

    def validateRelationships():
        valid = True
        validateMsg = ''
        # NB pyEphem can handle invalid date like 30/2; it changes it to 2/3.
        if params['month'] in (4,6,9,11):
            if params['day'] > 30:
                validateMsg += r'<p class="error">Day: %s is not a valid day for that month %s.</p>' % (params['day'], params['month'])
                valid = False
        if params['month'] == 2:
            if params['day'] > 29:
                validateMsg += r'<p class="error">Month: %s is not a valid day for month %s.</p>' % (params['day'], params['month'])
                valid = False
        if params['temp'] and not (-50 < params['temp'] < 60):
            validateMsg += r'<p class="error">Temp: %s is out of the allowed temperature range of -50C to +50C. (Did you use Fahrenheit?)</p>' % params['temp']
            valid = False
        if params['elev'] and not (-100 < params['elev'] < 10000):
            validateMsg += r'<p class="error">Elev: %s is out of the allowed elevation range of -100m to +10000m.<br /><small>(The maximum was chosen arbitrarily.  If you really need an elevation higher than 10,000m, email me.)</small></p>' % params['temp']
            valid = False
        if params['pressure'] and not (900 < params['pressure'] < 1100):
            validateMsg += r'<p class="error">Pressure: %s is out of the allowed pressure range of 900 mB to 1100mB.</p>' % params['temp']
            valid = False
        if params['minmag'] and not (-30 < params['minmag'] < 20):
            validateMsg += r'<p class="error">minmag: %s is out of the allowed minmagerature range of -30 to +20. </p>' % params['minmag']
            valid = False
        return valid, validateMsg

    validType, validateMsgType = validateTypes()
    if validType:                                       # Don't check if already in error because we might get invalid type error if input is wrong type.
        validRelationship, validateMsgRelationship = validateRelationships()
    return validType and validRelationship, validateMsgType + validateMsgRelationship


def renderErrors(validateMsg):
    print '<div id="output">'
    for line in validateMsg.splitlines():
        print line
    print '</div><!-- error -->'


def renderForm():
    city_list= ( 'Abu Dhabi', 'Adelaide', 'Almaty', 'Amsterdam', 'Antwerp', 'Arhus', 'Athens', 'Atlanta', 'Auckland', 'Baltimore', 'Bangalore', 'Bangkok', 'Barcelona', 'Beijing', 'Berlin', 'Birmingham', 'Bogota', 'Bologna', 'Boston', 'Bratislava', 'Brazilia', 'Brisbane', 'Brussels', 'Bucharest', 'Budapest', 'Buenos Aires', 'Cairo', 'Calgary', 'Cape Town', 'Caracas', 'Chicago', 'Cleveland', 'Cologne', 'Colombo', 'Columbus', 'Copenhagen', 'Dallas', 'Detroit', 'Dresden', 'Dubai', 'Dublin', 'Dusseldorf', 'Edinburgh', 'Frankfurt', 'Geneva', 'Genoa', 'Glasgow', 'Gothenburg', 'Guangzhou', 'Hamburg', 'Hanoi', 'Helsinki', 'Ho Chi Minh City', 'Hong Kong', 'Houston', 'Istanbul', 'Jakarta', 'Johannesburg', 'Kansas City', 'Kiev', 'Kuala Lumpur', 'Leeds', 'Lille', 'Lima', 'Lisbon', 'London', 'Los Angeles', 'Luxembourg', 'Lyon', 'Madrid', 'Manchester', 'Manila', 'Marseille', 'Melbourne', 'Mexico City', 'Miami', 'Milan', 'Minneapolis', 'Montevideo', 'Montreal', 'Moscow', 'Mumbai', 'Munich', 'New Delhi', 'New York', 'Osaka', 'Oslo', 'Paris', 'Perth, Aust', 'Philadelphia', 'Prague', 'Richmond', 'Rio de Janeiro', 'Riyadh', 'Rome', 'Rotterdam', 'San Francisco', 'Santiago', 'Sao Paulo', 'Seattle', 'Seoul', 'Shanghai', 'Singapore', 'St. Petersburg', 'Stockholm', 'Stuttgart', 'Sydney', 'Taipei', 'Tashkent', 'Tehran', 'Tel Aviv', 'The Hague', 'Tijuana', 'Tokyo', 'Toronto', 'Turin', 'Utrecht', 'Vancouver', 'Vienna', 'Warsaw', 'Washington', 'Wellington', 'Zurich')
    star_list = ( 'Achernar', 'Adara', 'Agena', 'Albereo', 'Alcaid', 'Alcor', 'Alcyone', 'Aldebaran', 'Alderamin', 'Alfirk', 'Algenib', 'Algieba', 'Algol', 'Alhena', 'Alioth', 'Almach', 'Alnair', 'Alnilam', 'Alnitak', 'Alphard', 'Alphecca', 'Alshain', 'Altair', 'Antares', 'Arcturus', 'Arkab Posterior', 'Arkab Prior', 'Arneb', 'Atlas', 'Bellatrix', 'Betelgeuse', 'Canopus', 'Capella', 'Caph', 'Castor', 'Cebalrai', 'Deneb', 'Denebola', 'Dubhe', 'Electra', 'Elnath', 'Enif', 'Etamin', 'Fomalhaut', 'Gienah Corvi', 'Hamal', 'Izar', 'Kaus Australis', 'Kochab', 'Maia', 'Markab', 'Megrez', 'Menkalinan', 'Menkar', 'Merak', 'Merope', 'Mimosa', 'Minkar', 'Mintaka', 'Mirach', 'Mirzam', 'Mizar', 'Naos', 'Nihal', 'Nunki', 'Peacock', 'Phecda', 'Polaris', 'Pollux', 'Procyon', 'Rasalgethi', 'Rasalhague', 'Regulus', 'Rigel', 'Rukbat', 'Sadalmelik', 'Sadr', 'Saiph', 'Scheat', 'Schedar', 'Shaula', 'Sheliak', 'Sirius', 'Sirrah', 'Spica', 'Sulafat', 'Tarazed', 'Taygeta', 'Thuban', 'Unukalhai', 'Vega', 'Vindemiatrix', 'Wezen', 'Zaurak')
    tz_list = ( 'US/Alaska', 'US/Arizona', 'US/Central', 'US/Eastern', 'US/Hawaii', 'US/Mountain', 'US/Pacific', 'Africa/Abidjan', 'Africa/Accra', 'Africa/Addis_Ababa', 'Africa/Algiers', 'Africa/Asmara', 'Africa/Bamako', 'Africa/Bangui', 'Africa/Banjul', 'Africa/Bissau', 'Africa/Blantyre', 'Africa/Brazzaville', 'Africa/Bujumbura', 'Africa/Cairo', 'Africa/Casablanca', 'Africa/Ceuta', 'Africa/Conakry', 'Africa/Dakar', 'Africa/Dar_es_Salaam', 'Africa/Djibouti', 'Africa/Douala', 'Africa/El_Aaiun', 'Africa/Freetown', 'Africa/Gaborone', 'Africa/Harare', 'Africa/Johannesburg', 'Africa/Kampala', 'Africa/Khartoum', 'Africa/Kigali', 'Africa/Kinshasa', 'Africa/Lagos', 'Africa/Libreville', 'Africa/Lome', 'Africa/Luanda', 'Africa/Lubumbashi', 'Africa/Lusaka', 'Africa/Malabo', 'Africa/Maputo', 'Africa/Maseru', 'Africa/Mbabane', 'Africa/Mogadishu', 'Africa/Monrovia', 'Africa/Nairobi', 'Africa/Ndjamena', 'Africa/Niamey', 'Africa/Nouakchott', 'Africa/Ouagadougou', 'Africa/Porto-Novo', 'Africa/Sao_Tome', 'Africa/Tripoli', 'Africa/Tunis', 'Africa/Windhoek', 'America/Adak', 'America/Anchorage', 'America/Anguilla', 'America/Antigua', 'America/Araguaina', 'America/Argentina/Buenos_Aires', 'America/Argentina/Catamarca', 'America/Argentina/Cordoba', 'America/Argentina/Jujuy', 'America/Argentina/La_Rioja', 'America/Argentina/Mendoza', 'America/Argentina/Rio_Gallegos', 'America/Argentina/Salta', 'America/Argentina/San_Juan', 'America/Argentina/San_Luis', 'America/Argentina/Tucuman', 'America/Argentina/Ushuaia', 'America/Aruba', 'America/Asuncion', 'America/Atikokan', 'America/Bahia', 'America/Bahia_Banderas', 'America/Barbados', 'America/Belem', 'America/Belize', 'America/Blanc-Sablon', 'America/Boa_Vista', 'America/Bogota', 'America/Boise', 'America/Cambridge_Bay', 'America/Campo_Grande', 'America/Cancun', 'America/Caracas', 'America/Cayenne', 'America/Cayman', 'America/Chicago', 'America/Chihuahua', 'America/Costa_Rica', 'America/Cuiaba', 'America/Curacao', 'America/Danmarkshavn', 'America/Dawson', 'America/Dawson_Creek', 'America/Denver', 'America/Detroit', 'America/Dominica', 'America/Edmonton', 'America/Eirunepe', 'America/El_Salvador', 'America/Fortaleza', 'America/Glace_Bay', 'America/Godthab', 'America/Goose_Bay', 'America/Grand_Turk', 'America/Grenada', 'America/Guadeloupe', 'America/Guatemala', 'America/Guayaquil', 'America/Guyana', 'America/Halifax', 'America/Havana', 'America/Hermosillo', 'America/Indiana/Indianapolis', 'America/Indiana/Knox', 'America/Indiana/Marengo', 'America/Indiana/Petersburg', 'America/Indiana/Tell_City', 'America/Indiana/Vevay', 'America/Indiana/Vincennes', 'America/Indiana/Winamac', 'America/Inuvik', 'America/Iqaluit', 'America/Jamaica', 'America/Juneau', 'America/Kentucky/Louisville', 'America/Kentucky/Monticello', 'America/La_Paz', 'America/Lima', 'America/Los_Angeles', 'America/Maceio', 'America/Managua', 'America/Manaus', 'America/Martinique', 'America/Matamoros', 'America/Mazatlan', 'America/Menominee', 'America/Merida', 'America/Mexico_City', 'America/Miquelon', 'America/Moncton', 'America/Monterrey', 'America/Montevideo', 'America/Montreal', 'America/Montserrat', 'America/Nassau', 'America/New_York', 'America/Nipigon', 'America/Nome', 'America/Noronha', 'America/North_Dakota/Center', 'America/North_Dakota/New_Salem', 'America/Ojinaga', 'America/Panama', 'America/Pangnirtung', 'America/Paramaribo', 'America/Phoenix', 'America/Port-au-Prince', 'America/Port_of_Spain', 'America/Porto_Velho', 'America/Puerto_Rico', 'America/Rainy_River', 'America/Rankin_Inlet', 'America/Recife', 'America/Regina', 'America/Resolute', 'America/Rio_Branco', 'America/Santa_Isabel', 'America/Santarem', 'America/Santiago', 'America/Santo_Domingo', 'America/Sao_Paulo', 'America/Scoresbysund', 'America/St_Johns', 'America/St_Kitts', 'America/St_Lucia', 'America/St_Thomas', 'America/St_Vincent', 'America/Swift_Current', 'America/Tegucigalpa', 'America/Thule', 'America/Thunder_Bay', 'America/Tijuana', 'America/Toronto', 'America/Tortola', 'America/Vancouver', 'America/Whitehorse', 'America/Winnipeg', 'America/Yakutat', 'America/Yellowknife', 'Antarctica/Casey', 'Antarctica/Davis', 'Antarctica/DumontDUrville', 'Antarctica/Macquarie', 'Antarctica/Mawson', 'Antarctica/McMurdo', 'Antarctica/Palmer', 'Antarctica/Rothera', 'Antarctica/Syowa', 'Antarctica/Vostok', 'Asia/Aden', 'Asia/Almaty', 'Asia/Amman', 'Asia/Anadyr', 'Asia/Aqtau', 'Asia/Aqtobe', 'Asia/Ashgabat', 'Asia/Baghdad', 'Asia/Bahrain', 'Asia/Baku', 'Asia/Bangkok', 'Asia/Beirut', 'Asia/Bishkek', 'Asia/Brunei', 'Asia/Choibalsan', 'Asia/Chongqing', 'Asia/Colombo', 'Asia/Damascus', 'Asia/Dhaka', 'Asia/Dili', 'Asia/Dubai', 'Asia/Dushanbe', 'Asia/Gaza', 'Asia/Harbin', 'Asia/Ho_Chi_Minh', 'Asia/Hong_Kong', 'Asia/Hovd', 'Asia/Irkutsk', 'Asia/Jakarta', 'Asia/Jayapura', 'Asia/Jerusalem', 'Asia/Kabul', 'Asia/Kamchatka', 'Asia/Karachi', 'Asia/Kashgar', 'Asia/Kathmandu', 'Asia/Kolkata', 'Asia/Krasnoyarsk', 'Asia/Kuala_Lumpur', 'Asia/Kuching', 'Asia/Kuwait', 'Asia/Macau', 'Asia/Magadan', 'Asia/Makassar', 'Asia/Manila', 'Asia/Muscat', 'Asia/Nicosia', 'Asia/Novokuznetsk', 'Asia/Novosibirsk', 'Asia/Omsk', 'Asia/Oral', 'Asia/Phnom_Penh', 'Asia/Pontianak', 'Asia/Pyongyang', 'Asia/Qatar', 'Asia/Qyzylorda', 'Asia/Rangoon', 'Asia/Riyadh', 'Asia/Sakhalin', 'Asia/Samarkand', 'Asia/Seoul', 'Asia/Shanghai', 'Asia/Singapore', 'Asia/Taipei', 'Asia/Tashkent', 'Asia/Tbilisi', 'Asia/Tehran', 'Asia/Thimphu', 'Asia/Tokyo', 'Asia/Ulaanbaatar', 'Asia/Urumqi', 'Asia/Vientiane', 'Asia/Vladivostok', 'Asia/Yakutsk', 'Asia/Yekaterinburg', 'Asia/Yerevan', 'Atlantic/Azores', 'Atlantic/Bermuda', 'Atlantic/Canary', 'Atlantic/Cape_Verde', 'Atlantic/Faroe', 'Atlantic/Madeira', 'Atlantic/Reykjavik', 'Atlantic/South_Georgia', 'Atlantic/St_Helena', 'Atlantic/Stanley', 'Australia/Adelaide', 'Australia/Brisbane', 'Australia/Broken_Hill', 'Australia/Currie', 'Australia/Darwin', 'Australia/Eucla', 'Australia/Hobart', 'Australia/Lindeman', 'Australia/Lord_Howe', 'Australia/Melbourne', 'Australia/Perth', 'Australia/Sydney', 'Canada/Atlantic', 'Canada/Central', 'Canada/Eastern', 'Canada/Mountain', 'Canada/Newfoundland', 'Canada/Pacific', 'Europe/Amsterdam', 'Europe/Andorra', 'Europe/Athens', 'Europe/Belgrade', 'Europe/Berlin', 'Europe/Brussels', 'Europe/Bucharest', 'Europe/Budapest', 'Europe/Chisinau', 'Europe/Copenhagen', 'Europe/Dublin', 'Europe/Gibraltar', 'Europe/Helsinki', 'Europe/Istanbul', 'Europe/Kaliningrad', 'Europe/Kiev', 'Europe/Lisbon', 'Europe/London', 'Europe/Luxembourg', 'Europe/Madrid', 'Europe/Malta', 'Europe/Minsk', 'Europe/Monaco', 'Europe/Moscow', 'Europe/Oslo', 'Europe/Paris', 'Europe/Prague', 'Europe/Riga', 'Europe/Rome', 'Europe/Samara', 'Europe/Simferopol', 'Europe/Sofia', 'Europe/Stockholm', 'Europe/Tallinn', 'Europe/Tirane', 'Europe/Uzhgorod', 'Europe/Vaduz', 'Europe/Vienna', 'Europe/Vilnius', 'Europe/Volgograd', 'Europe/Warsaw', 'Europe/Zaporozhye', 'Europe/Zurich', 'GMT', 'Indian/Antananarivo', 'Indian/Chagos', 'Indian/Christmas', 'Indian/Cocos', 'Indian/Comoro', 'Indian/Kerguelen', 'Indian/Mahe', 'Indian/Maldives', 'Indian/Mauritius', 'Indian/Mayotte', 'Indian/Reunion', 'Pacific/Apia', 'Pacific/Auckland', 'Pacific/Chatham', 'Pacific/Chuuk', 'Pacific/Easter', 'Pacific/Efate', 'Pacific/Enderbury', 'Pacific/Fakaofo', 'Pacific/Fiji', 'Pacific/Funafuti', 'Pacific/Galapagos', 'Pacific/Gambier', 'Pacific/Guadalcanal', 'Pacific/Guam', 'Pacific/Honolulu', 'Pacific/Johnston', 'Pacific/Kiritimati', 'Pacific/Kosrae', 'Pacific/Kwajalein', 'Pacific/Majuro', 'Pacific/Marquesas', 'Pacific/Midway', 'Pacific/Nauru', 'Pacific/Niue', 'Pacific/Norfolk', 'Pacific/Noumea', 'Pacific/Pago_Pago', 'Pacific/Palau', 'Pacific/Pitcairn', 'Pacific/Pohnpei', 'Pacific/Port_Moresby', 'Pacific/Rarotonga', 'Pacific/Saipan', 'Pacific/Tahiti', 'Pacific/Tarawa', 'Pacific/Tongatapu', 'Pacific/Wake', 'Pacific/Wallis')
    #city_list = ephem.cities._city_data.keys()     # this doesn't work, cities not found?
    #city_list.sort()
    messier_list = ( 'M1 Crab Nebula', 'M2', 'M3', 'M4', 'M5', 'M6 Butterfly Cluster', 'M7 Ptolemy\'s Cluster', 'M8 Lagoon Nebula', 'M9', 'M10', 'M11 Wild Duck Cluster', 'M12', 'M13 Hercules Cluster', 'M14', 'M15', 'M16 Eagle Nebula, Star Queen Nebula', 'M17 Omega Nebula, Swan Nebula, Lobster Nebula', 'M18', 'M19', 'M20 Trifid Nebula', 'M21', 'M22', 'M23', 'M24 Delle Caustiche', 'M25', 'M26', 'M27 Dumbbell Nebula', 'M28', 'M29', 'M30', 'M31 Andromeda Galaxy', 'M32', 'M33 Triangulum Galaxy', 'M34', 'M35', 'M36', 'M37', 'M38', 'M39', 'M40 Double Star WNC4', 'M41', 'M42 Orion Nebula', 'M43 de Mairan\'s nebula; part of Orion Nebula', 'M44 Praesepe, Beehive Cluster', 'M45 Subaru, Pleiades, Seven Sisters', 'M46', 'M47', 'M48', 'M49', 'M50', 'M51 Whirlpool Galaxy', 'M52', 'M53', 'M54', 'M55', 'M56', 'M57 Ring Nebula', 'M58', 'M59', 'M60', 'M61', 'M62', 'M63 Sunflower Galaxy', 'M64 Blackeye Galaxy', 'M65', 'M66', 'M67', 'M68', 'M69', 'M70', 'M71', 'M72', 'M73', 'M74', 'M75', 'M76 Little Dumbbell Nebula, Cork Nebula', 'M77', 'M78', 'M79', 'M80', 'M81 Bode\'s Galaxy', 'M82 Cigar Galaxy', 'M83 Southern Pinwheel Galaxy', 'M84', 'M85', 'M86', 'M87 Virgo A', 'M88', 'M89', 'M90', 'M91', 'M92', 'M93', 'M94', 'M95', 'M96', 'M97 Owl Nebula', 'M98', 'M99', 'M100', 'M101 Pinwheel Galaxy', 'M102 Spindle Galaxy', 'M103', 'M104 Sombrero Galaxy', 'M105', 'M106', 'M107', 'M108', 'M109', 'M110')
    form = {}
    checked = 'checked="checked"'                       # used often enough to treat it as a quasi constant
    selected = 'selected="selected"'
    hours = ''
    for h in range(0,24):
        h_ = str(h)
        if h_ == str(params['hour']):
            form['hourchecked'] = selected
        else:
            form['hourchecked'] = ''
        hours = "".join((hours, '<option value="%s" %s >%s</option>' % (h_, form['hourchecked'], h_)))
    hours = "".join((hours, '<option value="0" >0</option>'))         # append 0 to avoid unnecessary scrolling
    form['hours'] = hours
    minutes = ''
    for m in range(0,60):
        m_ = str(m)
        if m_ == str(params['minute']):
            form['minutechecked'] = selected
        else:
            form['minutechecked'] = ''
        minutes = "".join((minutes, '<option value="%s" %s >%02d</option>' % (m_, form['minutechecked'], m)))
    minutes = "".join((minutes, '<option value="00" >00</option>'))         # append 00 to avoid unnecessary scrolling
    form['minutes'] = minutes
    days = ''
    for d in range(1,32):
        d_ = str(d)
        if d_ == str(params['day']):
            form['daychecked'] = selected
        else:
            form['daychecked'] = ''
        days = "".join((days, '<option value="%s" %s >%s</option>' % (d_, form['daychecked'], d_)))
    form['days'] = days

    months = ''
    for m in range(1,13):
        m_ = str(m)
        if m_ == str(params['month']):
            form['monthchecked'] = selected
        else:
            form['monthchecked'] = ''
        months = "".join((months, '<option value="%s" %s >%02d</option>' % (m_, form['monthchecked'], m)))
    form['months'] = months

    form['year'] = params['year']
    if params['now']:
        form['nowchecked'] = checked 
    else:
        form['nowchecked'] =  ''

    if params['utc']:
        form['utcchecked'] = checked
        form['localchecked'] = ''
        zones = '<option value ="UTC" selected="selected">UTC</option>'
    else:
        form['utcchecked'] = ''
        form['localchecked'] = checked
        zones = '<option value ="UTC">UTC</option>'

    for z in tz_list:
        if params['tzname'] and z == params['tzname']:
            form['tzchecked'] = 'selected="selected"'
        else:
            form['tzchecked'] = ''
        zones = "".join((zones, '<option value="%s" %s>%s</option>' % (z, form['tzchecked'], z)))

    cities = '<option value=""></option>'
    for c in city_list:
        if params['city'] and c == params['city']:
            form['cityselect'] = 'selected="selected"'
        else:
            form['cityselect'] = ''
        #cities += '<option value="%s" %s>%s</option>' % (c, form['cityselect'], c)
        cities = "".join((cities,'<option value="%s" %s>%s</option>' % (c, form['cityselect'], c)))

    form['lat'] = params['lat'] or ''
    form['long'] = params['long'] or ''
    form['temp'] =  params['temp'] or ''
    form['elev'] = params['elev'] or ''
    form['pressure'] =  params['pressure'] or ''

    stars = '<option value=""></option>'
    params['star'] += ''                  # make sure star has at least one member
    for s in star_list:
        for ss in params['star']:
            if s == ss:
                form['starselect'] = selected
                break
        else:
            form['starselect'] = ''
        stars = "".join((stars, '<option value="%s" %s>%s</option>' % (s, form['starselect'], s)))

    messiers = '<option value=""></option>'
    params['messier'] += ''
    for m in messier_list:
        for mm in params['messier']:
            if m == mm:
                form['messierselect'] = selected
                break
        else:
            form['messierselect'] = ''
        messiers = "".join((messiers, '<option value="%s" %s>%s</option>' % (m, form['messierselect'], m)))

    if params['altaz']:
        form['altazchecked'] = (checked,'')
    else:
        form['altazchecked'] = ('',checked)

    print"""<div id="input">
    <form action="/ephem/index.cgi" method="post">
    <fieldset><legend><b>Time &amp; Date</b></legend>
    <table id="date_table">
    <tr align="center"><td>hour</td><td>minute</td><td>day</td><td>month</td><td>year</td><td> </td><td>Now</td></tr>
    <tr align="right"><td><select name="hour" onfocus="uncheckNow()">"""
    print hours
    print """</select></td>
        <td>:<select name="minute" onfocus="uncheckNow()">"""
    print minutes
    print """</select></td>
        <td><select name="day" onfocus="uncheckNow()">"""
    print days
    print "</select></td>"
    print '<td>/<select name="month" onfocus="uncheckNow()">'
    print months
    print "</select></td>"
    print '<td>/<input type="text" name="year" value="%(year)s" size="5" onfocus="uncheckNow()" /></td><td> or  </td><td><input type="checkbox" name="now" value="True" %(nowchecked)s /> </td><td> <input type="submit" value="Submit" /></td></tr></table><br />' %  form
    print """
    <table style="display: inline; margin: 0px; padding: 0px;">
    <tr><td>UTC</td><td><input type="radio" name="utc" value="True" %(utcchecked)s /></td></tr>
    <tr><td>Local</td><td><input type="radio" name="utc" value="False" %(localchecked)s /></td>
    <td>Timezone: <select name="tzname">
    """ % form
    print zones
    print """
    </select></td></tr></table></fieldset>
    <fieldset><legend><b>Location</b></legend>
    <fieldset><legend> Choose a city </legend>
    City:  <select name="city" onfocus="uncheckLocation()">
    """
    print  cities
    print """
    </select> <small>Overrides any latitude and longitude below</small></fieldset><fieldset><legend>or input location manually</legend>
    <small>West, South negative</small><br />
    Latitude: <input type="text" name="lat" value="%(lat)s" size="10" onfocus="uncheckCity()" /><small>DD:MM:SS or DD.dddd or DD:MM.mmm</small><br />
    Longitude: <input type="text" name="long" value="%(long)s" size="10" onfocus="uncheckCity()" /><br />
    <hr /><small>The entries below will also override the city settings (if you selected a city above).</small><br />
    Temperature: <input type="text" name="temp" value="%(temp)s" size="5" />°C  <small>default: 15°C</small><br />
    Elevation: <input type="text" name="elev" value="%(elev)s" size="5" />metres <small>default: 0.0m</small><br />
    Barometric Pressure: <input type="text" name="pressure" value="%(pressure)s" size="5" />mBar <small>default: 1010mB</small><br />
    </fieldset></fieldset>
    <fieldset><legend><b>Bodies</b></legend>
    <fieldset><legend>Solar System</legend>
    <input type="checkbox" name="sun" value="True" checked="checked" /> Sun<br />
    <input type="checkbox" name="moon" value="True" checked="checked" /> Moon<br />
    <input type="checkbox" name="mercury" value="True" checked="checked"/> Mercury<br />
    <input type="checkbox" name="venus" value="True" checked="checked"/> Venus<br />
    <input type="checkbox" name="mars" value="True" checked="checked"/> Mars<br />
    <input type="checkbox" name="jupiter" value="True" checked="checked"/> Jupiter<br />
    <input type="checkbox" name="saturn" value="True" checked="checked"/> Saturn<br />
    <input type="checkbox" name="uranus" value="True" checked="checked"/> Uranus<br />
    <input type="checkbox" name="neptune" value="True" checked="checked"/> Neptune<br />
    </fieldset><fieldset><legend>Stars &amp; Nebulae</legend>
    <small>Multiple selections use the control key.  For your convenience: <a href="http://en.wikipedia.org/wiki/List_of_Messier_objects" target=\"_blank\">list of Messiers</a></small><br /> 
    <select name="star" multiple="multiple" > """ % form
    print stars
    print '</select> <select name="messier" multiple="multiple" >'
    print messiers
    print """
    </select></fieldset></fieldset>
    <fieldset><legend>Results</legend>
    Display results in <br />&nbsp;&nbsp;Alt/Az &nbsp;<input type="radio" name="altaz" value="True" %s />
     <br />&nbsp;&nbsp;RA/Dec<input type="radio" name="altaz" value="False" %s />
     <br />Only objects above horizon?<input type="checkbox" name="above_horiz" value="True" %s />
     <br />Only brighter than<input type="text" value="%s" name="minmag" size="3" />magnitude (lower is brighter)
    </fieldset>
    <fieldset><legend><b>Go</b></legend>
    <input type="hidden" name="processed" value="True" />""" % ( form['altazchecked'] + (params['above_horiz'] and 'checked="checked"' or '',) + (params['minmag'] < 99 and params['minmag'] or '',))
    if params['save'] or not params['processed']:
        checked = 'checked="checked"'
    else:
        checked = ''
    print """Save settings: <input type="checkbox" name="save" value="True" %s />
    Clear settings: <input type="checkbox" name="clear" value="True" />
    <input type="submit" value="Submit" />
    </fieldset>
    </form></div><!-- input -->""" % checked


def setUTCDate():
    if params['utc']:
        params['utc_date'] = (params['year'], params['month'], params['day'], params['hour'], params['minute'], params['second'])
    else:
        # from http://stackoverflow.com/questions/1357711/pytz-utc-conversion
        d = datetime(params['year'], params['month'], params['day'], params['hour'], params['minute'], params['second'])
        tz = pytz.timezone(params['tzname'])
        _date = tz.normalize(tz.localize(d).astimezone(pytz.utc))
        params['utc_date'] = _date.utctimetuple()[:6]
        #print '_date is %s, utc is %s' %(_date, params['utc_date'])


def getLocalDateTime(date):
    # Input tuple, returns tuple.
    # NB Can't use ephem.localtime as that uses the machine's timezone info.
    # NB input as ephem.Date type, not datetime type.
    # from http://stackoverflow.com/questions/1357711/pytz-utc-conversion
    tz = pytz.timezone(params['tzname'])
    utc = pytz.utc
#    _date = datetime(*date)
#    temp = utc.localize(_date)
#    temp2= temp.astimezone(tz)
#    temp3 = utc.normalize(temp2)
#    return temp3.timetuple()
    return utc.normalize(utc.localize(datetime(*date)).astimezone(tz)).timetuple()


def getMessierEdb(m):
    # Returns a string giving a Messier edb, or None if not found.  
    # Note use of with...as syntax obviates need for f.close(): happens automatically when 'with' block exits.
    edb = None
    try:
        with open(messierdb) as f:
            for line in f:
                if line.startswith(m):
                    edb = line
                    break
    except:
        pass
    return edb

def getCrescentMoon(home, date):
    """ return the next date time in ephem format of crescent moon
    
    where sun has set and moon > 10 degrees above horizon after sun set"""
    moon_minimum = ephem.degrees('09:00:00')
    _home_date = home.date
    home.date = date
    home.date -= 1                              # take it back a day to ensure we find the real next crescent time
    s = ephem.Sun(home)
    m = ephem.Moon(home)
    home.date = home.next_setting(s)
    s.compute(home)
    m.compute(home)
    # This loop used to test for sunset before moonset, but since the calc date is set to sunset each
    # iteration, it is enough to test simply for moon alt > 9 at sunset, since if moonset was before sunset, 
    # the altitude would be negative.
    i = 0                                                           # loop counter to avoid ridiculous number of attempts
    while m.alt < moon_minimum:                                     # trap for the unwary: native angles are in radians and only display as angles.
        if i > 4:
            break
        i += 1
        home.date = home.next_setting(s)
        s.compute(home)
        m.compute(home)
    _temp = home.date
    home.date = _home_date                                  # restore original home.date
    return ephem.date(_temp + ephem.second)                # kludge to add 1 second to avoid clashing dictionary keys after the calling function

def getNextRiseSet(body, home):
    """ Returns tuples for next rise and set for body.  Assures home.date is not changed."""
    _home_date = home.date
    try:
        body.compute(home)
        rise = home.next_rising(body).tuple()
        home.date = _home_date
        body.compute(home)
        set = home.next_setting(body).tuple()
    except (ephem.AlwaysUpError, ephem.NeverUpError):
        rise,set = (-1,),(-1,)
    home.date = _home_date
    return rise, set


def renderHTMLIntro():
    print """
    <div id="intro"><a name="intro"></a>
    <h2>Ephemeris</h2>
    <h3>Introduction</h3>
    <p>This is an online general purpose ephemeris, a table that gives the positions of celestial objects.  It can display a range of information for the planets, the major stars and the <a href="/axs/ax.pl?http://en.wikipedia.org/wiki/Messier_object">Messier objects</a> as viewed from any location on Earth.  </p>
    <p>I designed it mainly for naked-eye or binocular work.  It is especially useful for situations like, "What is that bright object about 40 degrees up in the East".</p>
    <h3>Features</h3>
    <ul>
        <li>You can use your local time or UTC (GMT), whichever you prefer, or you can just click on the <em>Now</em> box.</li>
        <li>You can use the handy list of timezones to enter your timezone, which is needed if you are using your local time.</li>
        <li>You can choose your location from a list of provided cities, or you can enter your latitude and longitude in a variety of formats.</li>
        <li>You can fine tune things with the local temperature, pressure and altitude, but you don't have to.</li>
        <li>You get the seasons and the moon events.</li>
        <li>You get all the naked-eye visible planets.</li>
        <li>You can also select a range of common stars and messier objects.</li>
        <li><i>Hint:</i>To see if a constellation is up, select all stars, and choose "Only above the horizon".  Then sort list of stars by constellation.</li>
        <li>You can do some filtering to exclude irrelevant objects.</li>
        <li>You can save your settings for next time.</li>
        <li>Two <i>Submit</i> buttons, one top and one bottom, for when you are just changing the date and don't want to scroll down to the bottom button.</li>
    </ul>
    <h3>Usage</h3>
    <ul> 
    <li>Select the time and date, or choose Now.  Initially, it is set to current time in UTC.</li>
    <li>Select UTC or local time and your timezone.</li>
    <li>Select your location:</li>
        <ul>
            <li>a city from the drop-down list, or</li>
            <li>enter the latitude and longitude.</li>
        </ul>
    <li>Enter the temperature, elevation, and barometric pressure of your location, or leave them blank to use the defaults.</li>
    <ul>
        <li>These affect the angles only slightly.  You probably don't need to bother.</li>
        <li>Cities come with a default elevation (which is displayed in the output).  You don't need to set elevation if you chose a city.</li>
        <li>Barometric pressure is the sea level equivalent, i.e. the one that the TV and newspapers report.</li></ul></li>
        <li>Magnitude: magnitude is a measure of brightness (or dimness, if you prefer); the dimmer the object the higher the number.  The scale ranges from negative (very bright objects) to positive (dimmer objects). Most visible stars are between roughly 1&mdash;6. </li>
        <ul>
            <li>Typically, with the naked eye you can see up to about magnitude 3 objects in an urban area, and up to about 6 in a rural area.  Binoculars increase that quite a bit, up to about 9 in a rural area.</li>
        </ul>
    <li>Select which of the planets you wish to see (temporarily disabled; you get the lot, free!).</li>
    <li>Select none or more stars you wish to see (use the control key to select multiple stars; ctrl-a to select all of them).</li>
    <li>Do the same with the Messier objects.</li>
    <li>Choose whether to display the results in Altitude/Azimuth format, or in <a href="/axs/ax.pl?http://en.wikipedia.org/wiki/Declination">Right Angle/Declination</a> format.</li>
    <li>Choose to display only those objects that are above the horizon.</li>
    <li>Choose to display only those objects brighter than a certain value (the lower the value the more objects are filtered out; higher values will include dimmer objects).</li>
        <ul><li>Example: display only those objects brighter than mag 4 since you live in a city and cannot see dimmer objects anyway.  Enter 4 in the box.  The results will display everthing from magnitude -99 to 4 and will exclude everything from 4 to 99.</li></ul>
    <li>Choose to save settings, which stores your date, timezone and location information for later so you won't have to re-enter them again.  It uses cookies so it won't work if you have cookies disabled for this site.</li>
    <li>Clear settings removes any settings you have previously stored, e.g. you want to remove a saved city.  (It may not take effect until a browser restart.)</li>
    </ul>
    <h3>Output</h3>
    <ul>
    <li>You can sort the columns by clicking on the column heading.  Click again to reverse the sort.</li>
    <li>The rise and set times are always the <em>next</em> event in the immediate future.  This can be confusing if you are comparing times with other websites like <a href="http://www.heavens-above.com">heavens-above.com</a> that provide you with a previous and a next event. This ephemeris always looks forward.  If you want yesterday's times, change the date.<br />Set time may occur before rise time, or vice versa.  When a body is currently above the horizon, it sets before it rises next.  When the body is below the horizon, e.g. on the other side of the Earth, it rises before it sets.  You can tell which event occurs first by checking if the body is above or below the horizon currently.</li>
    <li>The <em>crescent moon</em> is the time of sunset immediately after the new moon (whose time may have been during the day), once the moon sets after the sun and it is at least 10° above the horizon (10° chosen arbitrarily&ndash;sometimes the crescent moon is only a couple of degrees above the horizon and you can't really see it). This may be the day of the new moon, or it may be a day or two later.  I included this for interest's sake as the new crescent moon is quite pretty.  It is not supposed to be accurate enough for religious observations; it does not take the height of the your horizon into account.</li>
    <li>Some stars either never set or never rise for your location, which means there is no set time or rise time.  In that case, the time is shown as -1 instead.</li>
    <li><em>TransAlt</em>, transit altitude, is the altitude at transit time, which is the time an object is the highest in the sky (i.e. passes through North).</li>
    <li><em>Local noon</em> is the time that the Sun is highest in the sky (the Sun's transit time).  Locations in the east of a timezone have their local noon earlier than locations in the west.</li>
    </ul>
    <h3>Restrictions</h3>
    <ul>
    <li><em>Date restrictions</em> are 1 A.D. &mdash; 9999 A.D., due to Python's date module which cannot go further back than 1 A.D.  The astronomical library I use can go further back, but I haven't implemented that feature because it would be a lot of work for the very few times it would be used.  Email me if this is an issue for you and I might change my mind.</li>
    <li>For years earlier than 1900, the local time and UTC time output is not formatted nicely due to a restriction in the <i>strftime</i> function in Python (restriction removed since 3.3).  This may result in odd displays such as "12:32:59.9999" instead of "12:33:00".</li>
    </ul>
    <h3>About</h3>
    <p>This is version 1.1, usable but not tidy.  It is written in python using the pyEphem module.  pyEphem uses the astro library from xephem, the well known Unix astronomy application.</p>
    <p>pyEphem made the astronomy calculations easy.  Almost all the development work was in data validation, getting cookies to work properly, and the html.</p>
    <p>Tested on google-chrome, opera and firefox.  Not yet tested on IE.</p>
    <h3>To Do</h3>
    <ul>
    <li>Add options to allow different fields in the output: next/prev rise/alt; transit time/alt.</li>
    <li>create star charts. I think I know how to do it and am now mulling over which projection method to use.  I'm leaning towards stereographic at the moment.</li>
    <li>Add ability to display satellite passes: ISS and Hubble.</li>
    </ul>
    <h3>Credit</h3>
    <p>The telescope icon is courtesy of the <a href="http://www.oxygen-icons.org/">Oxygen Icon Team</a> under the <a href="http://creativecommons.org/licenses/by-sa/3.0/">Creative Common Licence</a>.</p>
    <a href="#top">Top of page</a>
    </div><!-- intro -->
    """


if __name__ == '__main__':
    main()
