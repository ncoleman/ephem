#!/home/nickcoleman/local/bin/python
#coding=utf-8

import cgi, cgitb
import os
import Cookie
from datetime import datetime
from sys import exit
import ephem
import pytz

#   config variables
doctype = '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">'
baseurl = 'http://www.nickcoleman.org/ephem'
language = 'en'
keywords = 'ephemeris xephem pyephem python star sun moon'
content = 'web based ephemeris generated using python and pyephem'
title = 'Ephemeris'
# end config

# params notes:  date and time are stored as entered by user, utc_date tuple is that converted to UTC; utc is boolean indicating whether user is using UTC or local. now is used to indicate whether to override the date with the current time.
params = {
    'processed' : False,
    'now' : False,
    'save' : False,
    'minute' : None,
    'hour' : None,
    'day' : None,
    'month' : None,
    'year' : None,
    'utc_date' : (),
    'utc' : None,
    'tzname': None,
    'offset' : None,
    'city' : None,
    'lat' : None,
    'long' : None,
    'elev' : None,
    'temp' : None, 
    'pressure' : None,
    'star' : [],
    'body' : None,
    'sun' : None,
    'moon' : None,
    'mercury' : None,
    'venus' : None,
    'mars' : None,
    'jupiter' : None,
    'saturn' : None
}


def main():
    cgitb.enable()
    global params
    valid = True
    validMsg = ''
    cookie = Cookie.SimpleCookie()
    try:
        # validation not needed since it has been done before when the form was processed in the last session
        cookie.load(os.environ['HTTP_COOKIE'])
        for key in cookie.keys():
            if cookie[key].value == 'None' and not params.has_key(key):
                continue
            try:
                params[key] = int(cookie[key].value)        # convert to int if possible
            except ValueError:
                params[key] = cookie[key].value
        params['processed'] = True
        if params['hour']:                                  # use this as a proxy for 'yes, cookies were found'
            setUTCDate()
    except KeyError:
        pass
    #getCookies()
    cookiestring = ''
    cookiestringsplit = ''
#    try:
#        cookie.load(os.environ['HTTP_COOKIE'])       # get any cookies and fill in params
#        cookistring = cookie.output()
#        for key in cookie.keys():
#            value = cookie[key].value
#            if params.has_key(key) and value != 'None' and value != 0:
#                params[key] = value
#            cookiestringsplit += value
#    except KeyError:
#        cookiestring = 'Exception error in cookie load'
    form = cgi.FieldStorage()
    if form.has_key('processed'):                   # then this is the result of a POST
        for key in form.keys():                     # fill in params for any values POSTed
            params[key] = form.getvalue(key)
        params['star'] = form.getlist('star')                 # except that star is a special case
        if params['utc'] == 'UTC' or params['utc'] == 'True':
            params['utc'] = True                    # boolean makes it easier to test for subsequenctly
        else:
            params['utc'] = False                    # boolean makes it easier to test for subsequenctly
        if params['now'] == 'now' or params['now'] == 'True':
            params['now'] = True
        else:
            params['now'] = False
        valid, validMsg = validateParams()
        if params['now']:
            _date = datetime.utcnow().timetuple()[:5]
            if params['utc']:
                params['year'], params['month'], params['day'], params['hour'], params['minute'] = _date
            else:
                params['year'], params['month'], params['day'], params['hour'], params['minute'] = getLocalDateTime(_date)[:5]
        if valid:
            for key in ['minute', 'hour', 'day', 'month', 'year']:
                params[key] = int(params[key])          # tidy up params to correct type
            setUTCDate()
            for key in ['temp', 'pressure', 'elev']:
                try:
                    if params[key]:      # tidy to correct type *if it exists*
                        params[key] = float(params[key])
                except ValueError:
                    pass
        setCookies()
    print "Content-Type: text/html\n\n"
    renderHTMLHead()
    #print "<p>Environ: %s </p>" % os.environ
    #print "<p>Cookiestring: %s</p>" % cookiestring
    #print "<p>Cookiestringsplit: %s</p>" % cookiestringsplit
    if not valid:
        renderErrors(validMsg)
    print '<div id="forms">'
    renderForm()
    #print "<p>%s</p>" % os.environ
    print '<div id="output">'
    print "<p>Hello, pyephem</p>"
    #if params['processed']:
    if params['processed'] and valid:
        if params['city']:
            home = ephem.city(params['city'])
        elif params['lat'] and params['long']:
            home = ephem.Observer()
            home.name = 'User-provided'
            home.lat = params['lat']
            home.long = params['long']
            home.temp = 15.0        # will be overridden below if a value was manually entered
            home.elev = 0.0
            home.pressure = 1010.0
        else:
            params['city'] = 'Wembley'
            home = ephem.city(params['city'])
        if params['temp']:
            home.temp = float(params['temp'])
        if params['elev']:
            home.elev = float(params['elev'])
        if params['pressure']:
            home.pressure = float(params['pressure'])
        setUTCDate()
        home.date = ephem.Date(params['utc_date'])
        print '<p>Times are %s, except where specified.</p>' % (params['utc'] and 'UTC' or 'local for ' + params['tzname'])
        print "<p>Calculation time:  %s Local (%s UTC) Timezone: %s<br />Location:  %s, lat %s long %s,<br />Parameters: temperature %sC, elevation %4.0f metres, barometer %4.0f mBar.</p>" % (datetime(*getLocalDateTime(home.date.tuple())[:6]),  home.date, params['tzname'], home.name, home.lat, home.long, home.temp, home.elev, home.pressure)
        print '<table border="0" cellspacing="5"><tr><th></th><th>Altitude</th><th>Azimuth</th><th>Direction</th><th>Magnitude</th><th>Phase</th><th>%s Next Rise</th><th>Set</th></tr>' % (params['utc'] and 'UTC' or '')
        format = '<tr><td>%s</td><td>%s</td><td>%3s</td><td> %3s</td><td>%.0f</td><td>%.0f</td><td>%s</td><td>%s</td></tr>'
        params['sun'] = ephem.Sun(home)
        params['moon'] = ephem.Moon(home)
        params['mercury'] = ephem.Mercury(home)
        params['venus'] = ephem.Venus(home)
        params['mars'] = ephem.Mars(home)
        params['jupiter'] = ephem.Jupiter(home)
        params['saturn'] = ephem.Saturn(home)
        for body in ['sun','moon','mercury','venus','mars','jupiter','saturn']:
            if params['utc']:
                rtime = home.next_rising(params[body]).tuple()
                stime = home.next_setting(params[body]).tuple()
            else:
                rtime = getLocalDateTime(home.next_rising(params[body]).tuple())
                stime = getLocalDateTime(home.next_setting(params[body]).tuple())
            risetime = '%02.0f:%02.0f' % (rtime[3], rtime[4])
            settime = '%02.0f:%02.0f' % (stime[3], stime[4])
            params[body].compute(home)
            print format % (body.capitalize(), roundAngle(params[body].alt), roundAngle(params[body].az), azDirection(params[body].az), params[body].mag, params[body].phase, risetime, settime)
        print "<tr><td>-----</td></tr>"
        stars = []
        for s in params['star']:
            stars.append(ephem.star(s))
        for s in stars:
            try:
                if params['utc']:
                    rtime = home.next_rising(s).tuple()
                    stime = home.next_setting(s).tuple()
                else:
                    rtime = getLocalDateTime(home.next_rising(s).tuple())
                    stime = getLocalDateTime(home.next_setting(s).tuple())
                risetime = '%02.0f:%02.0f' % (rtime[3], rtime[4])
                settime = '%02.0f:%02.0f' % (stime[3], stime[4])
            except (ValueError):
                risetime = -1
                settime = -1
            s.compute(home)
            #print '<p>%s, az %s, alt %s, mag %2.0f</p>' % (s.name, roundAngle(s.az), roundAngle(s.alt), s.mag)
            print format % (s.name, roundAngle(s.alt), roundAngle(s.az), azDirection(s.az), s.mag, 0.0, risetime, settime)
        print '</table>'
        print "<p>Done.</p>"
    print """</div><!-- output -->
            </div><!-- forms -->"""
    renderHTMLIntro()
    renderHTMLFooter()


def roundAngle(angle):
    """ return the integer degrees part of the string representation of an angle"""
    # an alternative is some sort of variant of str(angle)[:2].  The problem is that the first few digits is variable, so splitting on ":" is better for all cases.
    return str(angle).split(":")[0]


def azDirection(az):
    """ return the direction (North, South, North-East etc, shown as N, S, NE) for an azimuth"""
    quadrant = int(round(az*180/ephem.pi/45.0))
    return {0:'N', 1:'NE', 2:'E',3:'SE',4:'S',5:'SW',6:'W',7:'NW',8:'N'}[quadrant]


def renderHTMLHead():
    print """<html><head>
        <META NAME="ephemeris xephem python" CONTENT="web based ephemeris written in Python using the pyephem">
    <script type="text/javascript">
    function uncheckNow() {
        var elements = document.getElementsByName('now');
        elements[0].checked = false;        // poss Bug: assumes only one element named 'now'
    }
    </script>
        <link rel=\"stylesheet\" href=\"ephemeris.css\" type=\"text/css\" />
        <title>Ephemeris</title>
    </head><body><div id="content"><a name="top"></a><h2>Ephemeris</h2><p><a href="#intro">Introduction</a> and help.</p>"""


def renderHTMLFooter():
    print """</div><!-- content -->
        </body></html>"""


def getCookies():
    global params
    cookie = Cookie.SimpleCookie()
    cookie.load(os.environ['HTTP_COOKIE'])
    for key in cookie.keys():
        params['key'] = cookie[key].value

def setCookies():
    if params['save']:
        cookie = Cookie.SimpleCookie()
        for key in ['hour', 'minute', 'day', 'month', 'year', 'utc', 'tzname', 'city', 'lat', 'long']: 
            cookie[key] = params[key]
            cookie[key]['expires'] = 63072000   # 2 years in seconds
            cookie[key]['path'] = '/ephem'
        print cookie.output()


def validateParams():
    validType = validateMsgType = True
    validRelationship = validateMsgRelationship = ''
    def validateTypes():
        import re
        valid = True
        validateMsg = ''
        # 00:00:00 or 00.0000
        if params['lat'] and not re.match(r'^([0-9]{1,3}(:[0-9]{1,3})+)|([0-9]*.[0-9]*)$',params['lat']):
            validateMsg += r'<p class="error">Latitude invalid.</p>'
            valid = False
        if params['long'] and not re.match(r'^([0-9]{1,3}(:[0-9]{1,3})+)|([0-9]*.[0-9]*)$',params['long']):
            validateMsg += r'<p class="error">Longitute invalid.</p>'
            valid = False
        # -/+ any 3 digit number plus floating part
        if params['temp'] and not re.match(r'^[-+]?[0-9]{1,3}(\.[0-9]*)*$', params['temp']):
            validateMsg += r'<p class="error">Temperature %s is invalid</p>' % params['temp']
            valid = False
        # any positive 4 digit number plus floating part
        if params['elev'] and not re.match(r'^[-+]?[0-9]{1,4}(\.[0-9]*)*$', params['elev']):
            validateMsg += r'<p class="error">Elevation %s is invalid</p>' % params['elev']
            #params['elev'] = 0.0
            valid = False
        if params['pressure'] and not re.match(r'^[0-9]{3,4}(\.[0-9]*)?$', params['pressure']):
            validateMsg += r'<p class="error">Pressure %s is invalid</p>' % params['pressure']
            valid = False
        if params['year'] and not re.match(r'^[0-9]{3,4}$', params['year']):
            validateMsg += r'<p class="error">Year %s is invalid</p>' % params['year']
            valid = False
        return valid, validateMsg

    def validateRelationships():
        valid = True
        validateMsg = ''
        if params['month'] in (4,6,9,11):
            if params['day'] > 30:
                validateMsg += r'<p class="error">Day: %s is not a valid day for that month $s.</p>' % (params['day'], params['month'])
                valid = False
        if params['month'] == 2:
            if params['day'] > 29:
                validateMsg += r'<p class="error">Month: %s is not a valid day for that month $s.</p>' % (params['day'], params['month'])
                valid = False
        if params['year'] == 2:
            validateMsg += r'<p class="error">Month: %s is not a valid day for that month $s.</p>' % (params['day'], params['month'])
            valid = False
        if params['temp'] and not (-50 < float(params['temp']) < 60):
            validateMsg += r'<p class="error">Temp: %s is out of the allowed temperature range of -50C to +50C. (Did you use Fahrenheit?)</p>' % params['temp']
            valid = False
        if params['elev'] and not (-100 < float(params['elev']) < 10000):
            validateMsg += r'<p class="error">Elev: %s is out of the allowed elevation range of -100m to +10000m.<br /><small>(The maximum was chosen arbitrarily.  If you really need an elevation higher than 10,000m, email me.)</small></p>' % params['temp']
            valid = False
        if params['pressure'] and not (900 < float(params['pressure']) < 1100):
            validateMsg += r'<p class="error">Pressure: %s is out of the allowed pressure range of 900 mB to 1100mB.</p>' % params['temp']
            valid = False
        return valid, validateMsg

    validType, validateMsgType = validateTypes()
    if validType:                                       # Don't check if already in error because we might get invalid type error if input is wrong type.
        validRelationship, validateMsgRelationship = validateRelationships()
    return validType and validRelationship, validateMsgType + validateMsgRelationship


def renderErrors(validateMsg):
    print '<div class="error">'
    for line in validateMsg.splitlines():
        print line
    print '</div><!-- error -->'


def renderForm():
    city_list= ( 'Abu Dhabi', 'Adelaide', 'Almaty', 'Amsterdam', 'Antwerp', 'Arhus', 'Athens', 'Atlanta', 'Auckland', 'Baltimore', 'Bangalore', 'Bangkok', 'Barcelona', 'Beijing', 'Berlin', 'Birmingham', 'Bogota', 'Bologna', 'Boston', 'Bratislava', 'Brazilia', 'Brisbane', 'Brussels', 'Bucharest', 'Budapest', 'Buenos Aires', 'Cairo', 'Calgary', 'Cape Town', 'Caracas', 'Chicago', 'Cleveland', 'Cologne', 'Colombo', 'Columbus', 'Copenhagen', 'Dallas', 'Detroit', 'Dresden', 'Dubai', 'Dublin', 'Dusseldorf', 'Edinburgh', 'Frankfurt', 'Geneva', 'Genoa', 'Glasgow', 'Gothenburg', 'Guangzhou', 'Hamburg', 'Hanoi', 'Helsinki', 'Ho Chi Minh City', 'Hong Kong', 'Houston', 'Istanbul', 'Jakarta', 'Johannesburg', 'Kansas City', 'Kiev', 'Kuala Lumpur', 'Leeds', 'Lille', 'Lima', 'Lisbon', 'London', 'Los Angeles', 'Luxembourg', 'Lyon', 'Madrid', 'Manchester', 'Manila', 'Marseille', 'Melbourne', 'Mexico City', 'Miami', 'Milan', 'Minneapolis', 'Montevideo', 'Montreal', 'Moscow', 'Mumbai', 'Munich', 'New Delhi', 'New York', 'Osaka', 'Oslo', 'Paris', 'Perth, Aust', 'Philadelphia', 'Prague', 'Richmond', 'Rio de Janeiro', 'Riyadh', 'Rome', 'Rotterdam', 'San Francisco', 'Santiago', 'Sao Paulo', 'Seattle', 'Seoul', 'Shanghai', 'Singapore', 'St. Petersburg', 'Stockholm', 'Stuttgart', 'Sydney', 'Taipei', 'Tashkent', 'Tehran', 'Tel Aviv', 'The Hague', 'Tijuana', 'Tokyo', 'Toronto', 'Turin', 'Utrecht', 'Vancouver', 'Vienna', 'Warsaw', 'Washington', 'Wellington', 'Wembley', 'Zurich')
    star_list = ( 'Achernar', 'Adara', 'Agena', 'Albereo', 'Alcaid', 'Alcor', 'Alcyone', 'Aldebaran', 'Alderamin', 'Alfirk', 'Algenib', 'Algieba', 'Algol', 'Alhena', 'Alioth', 'Almach', 'Alnair', 'Alnilam', 'Alnitak', 'Alphard', 'Alphecca', 'Alshain', 'Altair', 'Antares', 'Arcturus', 'Arkab Posterior', 'Arkab Prior', 'Arneb', 'Atlas', 'Bellatrix', 'Betelgeuse', 'Canopus', 'Capella', 'Caph', 'Castor', 'Cebalrai', 'Deneb', 'Denebola', 'Dubhe', 'Electra', 'Elnath', 'Enif', 'Etamin', 'Fomalhaut', 'Gienah Corvi', 'Hamal', 'Izar', 'Kaus Australis', 'Kochab', 'Maia', 'Markab', 'Megrez', 'Menkalinan', 'Menkar', 'Merak', 'Merope', 'Mimosa', 'Minkar', 'Mintaka', 'Mirach', 'Mirzam', 'Mizar', 'Naos', 'Nihal', 'Nunki', 'Peacock', 'Phecda', 'Polaris', 'Pollux', 'Procyon', 'Rasalgethi', 'Rasalhague', 'Regulus', 'Rigel', 'Rukbat', 'Sadalmelik', 'Sadr', 'Saiph', 'Scheat', 'Schedar', 'Shaula', 'Sheliak', 'Sirius', 'Sirrah', 'Spica', 'Sulafat', 'Tarazed', 'Taygeta', 'Thuban', 'Unukalhai', 'Vega', 'Vindemiatrix', 'Wezen', 'Zaurak')
    tz_list = ( 'US/Alaska', 'US/Arizona', 'US/Central', 'US/Eastern', 'US/Hawaii', 'US/Mountain', 'US/Pacific', 'Africa/Abidjan', 'Africa/Accra', 'Africa/Addis_Ababa', 'Africa/Algiers', 'Africa/Asmara', 'Africa/Bamako', 'Africa/Bangui', 'Africa/Banjul', 'Africa/Bissau', 'Africa/Blantyre', 'Africa/Brazzaville', 'Africa/Bujumbura', 'Africa/Cairo', 'Africa/Casablanca', 'Africa/Ceuta', 'Africa/Conakry', 'Africa/Dakar', 'Africa/Dar_es_Salaam', 'Africa/Djibouti', 'Africa/Douala', 'Africa/El_Aaiun', 'Africa/Freetown', 'Africa/Gaborone', 'Africa/Harare', 'Africa/Johannesburg', 'Africa/Kampala', 'Africa/Khartoum', 'Africa/Kigali', 'Africa/Kinshasa', 'Africa/Lagos', 'Africa/Libreville', 'Africa/Lome', 'Africa/Luanda', 'Africa/Lubumbashi', 'Africa/Lusaka', 'Africa/Malabo', 'Africa/Maputo', 'Africa/Maseru', 'Africa/Mbabane', 'Africa/Mogadishu', 'Africa/Monrovia', 'Africa/Nairobi', 'Africa/Ndjamena', 'Africa/Niamey', 'Africa/Nouakchott', 'Africa/Ouagadougou', 'Africa/Porto-Novo', 'Africa/Sao_Tome', 'Africa/Tripoli', 'Africa/Tunis', 'Africa/Windhoek', 'America/Adak', 'America/Anchorage', 'America/Anguilla', 'America/Antigua', 'America/Araguaina', 'America/Argentina/Buenos_Aires', 'America/Argentina/Catamarca', 'America/Argentina/Cordoba', 'America/Argentina/Jujuy', 'America/Argentina/La_Rioja', 'America/Argentina/Mendoza', 'America/Argentina/Rio_Gallegos', 'America/Argentina/Salta', 'America/Argentina/San_Juan', 'America/Argentina/San_Luis', 'America/Argentina/Tucuman', 'America/Argentina/Ushuaia', 'America/Aruba', 'America/Asuncion', 'America/Atikokan', 'America/Bahia', 'America/Bahia_Banderas', 'America/Barbados', 'America/Belem', 'America/Belize', 'America/Blanc-Sablon', 'America/Boa_Vista', 'America/Bogota', 'America/Boise', 'America/Cambridge_Bay', 'America/Campo_Grande', 'America/Cancun', 'America/Caracas', 'America/Cayenne', 'America/Cayman', 'America/Chicago', 'America/Chihuahua', 'America/Costa_Rica', 'America/Cuiaba', 'America/Curacao', 'America/Danmarkshavn', 'America/Dawson', 'America/Dawson_Creek', 'America/Denver', 'America/Detroit', 'America/Dominica', 'America/Edmonton', 'America/Eirunepe', 'America/El_Salvador', 'America/Fortaleza', 'America/Glace_Bay', 'America/Godthab', 'America/Goose_Bay', 'America/Grand_Turk', 'America/Grenada', 'America/Guadeloupe', 'America/Guatemala', 'America/Guayaquil', 'America/Guyana', 'America/Halifax', 'America/Havana', 'America/Hermosillo', 'America/Indiana/Indianapolis', 'America/Indiana/Knox', 'America/Indiana/Marengo', 'America/Indiana/Petersburg', 'America/Indiana/Tell_City', 'America/Indiana/Vevay', 'America/Indiana/Vincennes', 'America/Indiana/Winamac', 'America/Inuvik', 'America/Iqaluit', 'America/Jamaica', 'America/Juneau', 'America/Kentucky/Louisville', 'America/Kentucky/Monticello', 'America/La_Paz', 'America/Lima', 'America/Los_Angeles', 'America/Maceio', 'America/Managua', 'America/Manaus', 'America/Martinique', 'America/Matamoros', 'America/Mazatlan', 'America/Menominee', 'America/Merida', 'America/Mexico_City', 'America/Miquelon', 'America/Moncton', 'America/Monterrey', 'America/Montevideo', 'America/Montreal', 'America/Montserrat', 'America/Nassau', 'America/New_York', 'America/Nipigon', 'America/Nome', 'America/Noronha', 'America/North_Dakota/Center', 'America/North_Dakota/New_Salem', 'America/Ojinaga', 'America/Panama', 'America/Pangnirtung', 'America/Paramaribo', 'America/Phoenix', 'America/Port-au-Prince', 'America/Port_of_Spain', 'America/Porto_Velho', 'America/Puerto_Rico', 'America/Rainy_River', 'America/Rankin_Inlet', 'America/Recife', 'America/Regina', 'America/Resolute', 'America/Rio_Branco', 'America/Santa_Isabel', 'America/Santarem', 'America/Santiago', 'America/Santo_Domingo', 'America/Sao_Paulo', 'America/Scoresbysund', 'America/St_Johns', 'America/St_Kitts', 'America/St_Lucia', 'America/St_Thomas', 'America/St_Vincent', 'America/Swift_Current', 'America/Tegucigalpa', 'America/Thule', 'America/Thunder_Bay', 'America/Tijuana', 'America/Toronto', 'America/Tortola', 'America/Vancouver', 'America/Whitehorse', 'America/Winnipeg', 'America/Yakutat', 'America/Yellowknife', 'Antarctica/Casey', 'Antarctica/Davis', 'Antarctica/DumontDUrville', 'Antarctica/Macquarie', 'Antarctica/Mawson', 'Antarctica/McMurdo', 'Antarctica/Palmer', 'Antarctica/Rothera', 'Antarctica/Syowa', 'Antarctica/Vostok', 'Asia/Aden', 'Asia/Almaty', 'Asia/Amman', 'Asia/Anadyr', 'Asia/Aqtau', 'Asia/Aqtobe', 'Asia/Ashgabat', 'Asia/Baghdad', 'Asia/Bahrain', 'Asia/Baku', 'Asia/Bangkok', 'Asia/Beirut', 'Asia/Bishkek', 'Asia/Brunei', 'Asia/Choibalsan', 'Asia/Chongqing', 'Asia/Colombo', 'Asia/Damascus', 'Asia/Dhaka', 'Asia/Dili', 'Asia/Dubai', 'Asia/Dushanbe', 'Asia/Gaza', 'Asia/Harbin', 'Asia/Ho_Chi_Minh', 'Asia/Hong_Kong', 'Asia/Hovd', 'Asia/Irkutsk', 'Asia/Jakarta', 'Asia/Jayapura', 'Asia/Jerusalem', 'Asia/Kabul', 'Asia/Kamchatka', 'Asia/Karachi', 'Asia/Kashgar', 'Asia/Kathmandu', 'Asia/Kolkata', 'Asia/Krasnoyarsk', 'Asia/Kuala_Lumpur', 'Asia/Kuching', 'Asia/Kuwait', 'Asia/Macau', 'Asia/Magadan', 'Asia/Makassar', 'Asia/Manila', 'Asia/Muscat', 'Asia/Nicosia', 'Asia/Novokuznetsk', 'Asia/Novosibirsk', 'Asia/Omsk', 'Asia/Oral', 'Asia/Phnom_Penh', 'Asia/Pontianak', 'Asia/Pyongyang', 'Asia/Qatar', 'Asia/Qyzylorda', 'Asia/Rangoon', 'Asia/Riyadh', 'Asia/Sakhalin', 'Asia/Samarkand', 'Asia/Seoul', 'Asia/Shanghai', 'Asia/Singapore', 'Asia/Taipei', 'Asia/Tashkent', 'Asia/Tbilisi', 'Asia/Tehran', 'Asia/Thimphu', 'Asia/Tokyo', 'Asia/Ulaanbaatar', 'Asia/Urumqi', 'Asia/Vientiane', 'Asia/Vladivostok', 'Asia/Yakutsk', 'Asia/Yekaterinburg', 'Asia/Yerevan', 'Atlantic/Azores', 'Atlantic/Bermuda', 'Atlantic/Canary', 'Atlantic/Cape_Verde', 'Atlantic/Faroe', 'Atlantic/Madeira', 'Atlantic/Reykjavik', 'Atlantic/South_Georgia', 'Atlantic/St_Helena', 'Atlantic/Stanley', 'Australia/Adelaide', 'Australia/Brisbane', 'Australia/Broken_Hill', 'Australia/Currie', 'Australia/Darwin', 'Australia/Eucla', 'Australia/Hobart', 'Australia/Lindeman', 'Australia/Lord_Howe', 'Australia/Melbourne', 'Australia/Perth', 'Australia/Sydney', 'Canada/Atlantic', 'Canada/Central', 'Canada/Eastern', 'Canada/Mountain', 'Canada/Newfoundland', 'Canada/Pacific', 'Europe/Amsterdam', 'Europe/Andorra', 'Europe/Athens', 'Europe/Belgrade', 'Europe/Berlin', 'Europe/Brussels', 'Europe/Bucharest', 'Europe/Budapest', 'Europe/Chisinau', 'Europe/Copenhagen', 'Europe/Dublin', 'Europe/Gibraltar', 'Europe/Helsinki', 'Europe/Istanbul', 'Europe/Kaliningrad', 'Europe/Kiev', 'Europe/Lisbon', 'Europe/London', 'Europe/Luxembourg', 'Europe/Madrid', 'Europe/Malta', 'Europe/Minsk', 'Europe/Monaco', 'Europe/Moscow', 'Europe/Oslo', 'Europe/Paris', 'Europe/Prague', 'Europe/Riga', 'Europe/Rome', 'Europe/Samara', 'Europe/Simferopol', 'Europe/Sofia', 'Europe/Stockholm', 'Europe/Tallinn', 'Europe/Tirane', 'Europe/Uzhgorod', 'Europe/Vaduz', 'Europe/Vienna', 'Europe/Vilnius', 'Europe/Volgograd', 'Europe/Warsaw', 'Europe/Zaporozhye', 'Europe/Zurich', 'GMT', 'Indian/Antananarivo', 'Indian/Chagos', 'Indian/Christmas', 'Indian/Cocos', 'Indian/Comoro', 'Indian/Kerguelen', 'Indian/Mahe', 'Indian/Maldives', 'Indian/Mauritius', 'Indian/Mayotte', 'Indian/Reunion', 'Pacific/Apia', 'Pacific/Auckland', 'Pacific/Chatham', 'Pacific/Chuuk', 'Pacific/Easter', 'Pacific/Efate', 'Pacific/Enderbury', 'Pacific/Fakaofo', 'Pacific/Fiji', 'Pacific/Funafuti', 'Pacific/Galapagos', 'Pacific/Gambier', 'Pacific/Guadalcanal', 'Pacific/Guam', 'Pacific/Honolulu', 'Pacific/Johnston', 'Pacific/Kiritimati', 'Pacific/Kosrae', 'Pacific/Kwajalein', 'Pacific/Majuro', 'Pacific/Marquesas', 'Pacific/Midway', 'Pacific/Nauru', 'Pacific/Niue', 'Pacific/Norfolk', 'Pacific/Noumea', 'Pacific/Pago_Pago', 'Pacific/Palau', 'Pacific/Pitcairn', 'Pacific/Pohnpei', 'Pacific/Port_Moresby', 'Pacific/Rarotonga', 'Pacific/Saipan', 'Pacific/Tahiti', 'Pacific/Tarawa', 'Pacific/Tongatapu', 'Pacific/Wake', 'Pacific/Wallis')
    #city_list = ephem.cities._city_data.keys()     # this doesn't work, cities not found?
    #city_list.sort()
    print"""<div id="input">
    <form action="/ephem/index.cgi" method="POST">"""
    #print "<p>TEST day, month, year %s %s %s,</p>" % (params['day'], params['month'], params['year'])
    date = ephem.now().tuple()
    if not params['minute']:
        params['minute'] = int(date[4])
    if not params['hour']:
        params['hour'] = date[3]
    if not params['day']:
        params['day'] = date[2]
    if not params['month']:
       params['month'] = date[1]
    if not params['year']:
        params['year'] = date[0]
    print "<fieldset><legend><b>Time & Date</b></legend>"
    print """
    <table border="0" cellspacing="10" cellpadding="0"><tr align="center"><td>hour</td><td>minute</td><td>day</td><td>month</td><td>year</td><td> </td><td>Now</td></tr>
    <tr align="right"><td><select name="hour" onfocus="uncheckNow()">"""
    hours = ''
    for h in range(0,24):
        if str(h) == str(params['hour']):
            hours += '<option value="' + str(h) + '" selected>' + str(h) + '</option>'
        else:
            hours += '<option value="' + str(h) + '" >' + str(h) + '</option>'
    print hours
    print "</select></td> "
    print '<td><select name="minute" onfocus="uncheckNow()">'
    minutes = ''
    for m in range(0,60):
        if str(m) == str(params['minute']):
            minutes += '<option value="' + str(m) + '" selected>' + str(m) + '</option>'
        else:
            minutes += '<option value="' + str(m) + '" >' + str(m) + '</option>'
    print minutes
    print "</select></td> "
    print '<td><select name="day" onfocus="uncheckNow()">'
    days = ''
    for d in range(1,32):
        if str(d) == str(params['day']):
            days += '<option value="' + str(d) + '" selected>' + str(d) + '</option>'
        else:
            days += '<option value="' + str(d) + '" >' + str(d) + '</option>'
    print days
    print "</select></td>"
    print '<td><select name="month" onfocus="uncheckNow()">'
    months = ''
    for m in range(1,13):
        if str(m) == str(params['month']):
            months += '<option value="' + str(m) + '" selected>' + str(m) + '</option>'
        else:
            months += '<option value="' + str(m) + '" >' + str(m) + '</option>'
    print months
    print "</select></td>"
    if params['now']:
        checked = 'checked'
    else:
        checked = ''
    print '<td><input type="text" name="year" value="%s" size="5" onfocus="uncheckNow()" /></td><td> or  </td><td><input type="checkbox" name="now" value="now" %s /></td></tr></table><br />' % (params['year'], checked)
    if params['utc']:
        checked = ('checked', '')
    else:
        checked = ('', 'checked')
    print ' UTC <input type="radio" name="utc" value="UTC" %s /><br />Local <input type="radio" name="utc" value="local" %s /> ' % checked
    if params['offset']:
        checked = params['offset']
    else:
        checked = 0.0
    print 'Timezone: <select name="tzname">'
    if params['utc']:
        zones = '<option value ="UTC" selected>UTC</option>'
    else:
        zones = '<option value ="UTC">UTC</option>'
    for z in tz_list:
        checked = ''
        if params['tzname'] and z == params['tzname']:
            checked = "selected"
        zones += '<option value="%s" %s>%s</option>' % (z, checked, z)
    print zones
    print """</select></fieldset>
    <fieldset><legend><b>Location</b></legend>
    <fieldset><legend>Choose a city</legend>
    City:  <select name="city">"""
    cities = '<option value=""></option>'
    for c in city_list:
        if params['city'] and c == params['city']:
            cities += '<option value=\"' + c + '\" selected>' + c + '</option>'
        else:
            cities += '<option value=\"' + c + '\">' + c + '</option>'
    print  cities
    print """
    </select> <small>Overrides any latitude and longitude below</small></fieldset><fieldset><legend>or input location manually</legend>
    <small>West, South negative</small><br />"""
    if params['lat']:
        print 'Latitude: <input type="text" name="lat" value="%s" size="10" /><small>DD:MM:SS or DD.dddd or DD:MM.mmm</small><br />' % params['lat']
    else:
        print 'Latitude: <input type="text" name="lat" value="" size="10" /><small>DD:MM:SS or DD.dddd or DD:MM.mmm</small><br />'
    if params['long']:
        print 'Longitude: <input type="text" name="long" value="%s"size="10" /><br />' % params['long']
    else:
        print 'Longitude: <input type="text" name="long" value=""size="10" /><br />'
    print "<hr /><small>The entries below will also override the city settings (if you selected a city above).</small><br />"
    if params['temp']:
        print 'Temperature: <input type="text" name="temp" value="%s"size="5" />C  <small>default: 15C.</small><br />' % params['temp']
    else:
        print 'Temperature: <input type="text" name="temp" value=""size="5" />C  <small>default: 15C.</small><br />'
    if params['elev']:
        print  'Elevation: <input type="text" name="elev" value="%s"size="5" />metres <small>default: 0.0m</small><br />' % params['elev']
    else:
        print  'Elevation: <input type="text" name="elev" value=""size="5" />metres <small>default: 0.0m</small><br />'
    if params['pressure']:
        print 'Barometric Pressure: <input type="text" name="pressure" value="%s"size="5" />mBar <small>default: 1010mB</small><br />' % params['pressure']
    else:
        print 'Barometric Pressure: <input type="text" name="pressure" value=""size="5" />mBar <small>default: 1010mB</small><br />'
    print """
    </fieldset></fieldset>
    <fieldset><legend><b>Bodies</b></legend>
    <fieldset><legend>Solar System</legend>
    <input type="checkbox" name="sun" value="True" checked /> Sun<br />
    <input type="checkbox" name="moon" value="True" checked /> Moon<br />
    <input type="checkbox" name="mercury" value="True" checked/> Mercury<br />
    <input type="checkbox" name="venus" value="True" checked/> Venus<br />
    <input type="checkbox" name="mars" value="True" checked/> Mars<br />
    <input type="checkbox" name="jupiter" value="True" checked/> Jupiter<br />
    <input type="checkbox" name="saturn" value="True" checked/> Saturn<br />
    </fieldset><fieldset><legend>Stars</legend>
    <small>Multiple selections use the control key</small><br />
    <select name="star" multiple align="bottom"> """
    stars = '<option value=""></option>'
    params['star'] += ''                  # make sure star has at least one member
    for s in star_list:
        for ss in params['star']:
            if s == ss:
                stars += '<option value=\"' + s + '\" selected>' + s + '</option>'
                break
        else:
            stars += '<option value=\"' + s + '\">' + s + '</option>'
    print stars
    print """</select></fieldset></fieldset>
    <fieldset><legend><b>Go</b></legend>
    <input type="hidden" name="processed" value="True" />"""
    if params['save']:
        checked = 'checked'
    else:
        checked = ''
    print """Save settings: <input type="checkbox" name="save" value="True" %s />
    <input type="submit" value="Submit" />
    </fieldset>
    </form></div><!-- input -->""" % checked


def setUTCDate():
    if params['utc']:
        params['utc_date'] = (params['year'], params['month'], params['day'], params['hour'], params['minute'])
    else:
        # from http://stackoverflow.com/questions/1357711/pytz-utc-conversion
        d = datetime(params['year'], params['month'], params['day'], params['hour'], params['minute'])
        tz = pytz.timezone(params['tzname'])
        _date = tz.normalize(tz.localize(d).astimezone(pytz.utc))
        params['utc_date'] = _date.utctimetuple()[:6]
        #print '_date is %s, utc is %s' %(_date, params['utc_date'])


def getLocalDateTime(date):
    # NB Can't use ephem.localtime as that uses the machine's timezone info.
    # NB assumes this comes in as ephem.Date type, not datetime type
    # returns tuple
    # from http://stackoverflow.com/questions/1357711/pytz-utc-conversion
    tz = pytz.timezone(params['tzname'])
    utc = pytz.utc
#    _date = datetime(*date)
#    temp = utc.localize(_date)
#    temp2= temp.astimezone(tz)
#    temp3 = utc.normalize(temp2)
#    return temp3.timetuple()
    return utc.normalize(utc.localize(datetime(*date)).astimezone(tz)).timetuple()



def renderHTMLIntro():
    print """
    <div id="intro"><a name="intro"></a>
    <h1>Ephemeris</h1>
    <p>This is a general purpose ephemeris.  It can display a range of information for the planets and the major stars as viewed from any location on Earth.  </p>
    <p>Major cities can be selected from the drop-down list, or you can enter a latitude and longitude.</p>
    <p>Use either UTC or local timezone to select the time.</p>
    <h4>Use</h4>
    <ul> 
    <li>Select the time and date.  Initially, it is set to current time UTC.</li>
    <li>Select UTC or local time and select your timezone.</li>
    <li>Select a city, or</li>
    <li>Enter the latitude and longitude.</li>
    <li>Enter the temperature, elevation, and barometric pressure of your location, or leave them blank to use the defaults.<ul>
        <li>Each city has its own default elevation, which is displayed in the output.</li>
        <li>Barometric pressure is the sea level equivalent, i.e. the one that the TV and newspaper report.</li></ul></li>
    <li>Select which of the planets you wish to see (temporarily disabled; you get the lot, free!).</li>
    <li>Select one or more stars you wish to see (use the control key to select multiple stars).</li>
    <li>Save settings stores your date, timezone and location information for later.  It uses cookies so it won't work if you have cookies disabled for this site.</li>
    </ul>
    <h4>Output</h4>
    <ul>
    <li>The next rise and set times are <i>always</i> in the immediate future.  That means the next set may be before the next rise or vice versa. When the body is currently above the horizon, setting occurs before the next rising. When the body is below the horizon, e.g. on the other side of the Earth, it will rise before it sets next.  <br />You can tell which event occurs next by checking if the body is above or below the horizon currently: if above, the next event will be the set, followed by the rise; if below, the next event will be the rise followed by the set.</li>
    <li>Some stars either never set or never rise for your location, which means there is no set time or rise time.  In that case, the time is shown as -1 instead.</li>
    </ul>
    <h4>About</h4>
    <p>This is version 1.0, usable but not tidy or complete yet.  It is written in python using the pyEphem module.  pyEphem uses the astro library from xephem, the well known Unix astronomy application.</p>
    <p>pyEphem made the astronomy calculations easy.  Almost all the development work was in data validation, getting cookies to work properly, and the html.</p>
    <h4>To Do</h4>
    <ul>
    <!-- <li>Get saved settings working.  The cookies implementation is not working properly, so I've disabled it.</li> -->
    <!-- <li>Fix Moon next rise bug.</li> -->
    <li>Add options to allow different fields in the output: next/prev rise/alt; transit time/alt.</li>
    <!--
    <li>Get local vs UTC sorted out and working correctly</li>
    <li>Work out how to programatically calculate timezone offsets so I can display times in the user's local time.</li> -->
    <li>create star charts. I think I know how to do it and am now mulling over which projection method to use.  I'm leaning towards stereographic at the moment.</li>
    <li>tidy up the planets output.</li>
    <li>tidy up the stars output</li>
    <li>Tidy up the HTML to be standards compliant with doctype, correct meta headers, and so on.
    </ul>
    <a href="#top">Top of page</a>
    </div><!-- intro -->
    """


if __name__ == '__main__':
    main()
