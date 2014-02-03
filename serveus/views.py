import os, math, time, datetime, zipfile, base64, hashlib, glob, sqlite3
import xml.etree.ElementTree as ET
from functools import wraps
from flask import render_template, flash, redirect, request, url_for, make_response, abort
from flask.ext.login import login_user, current_user, LoginManager, logout_user, login_required
#from flask.ext.wtf import Required
from flask.ext.wtf import Form
from wtforms import TextField, BooleanField
from wtforms.validators import Required
from serveus import app
from forms import LoginForm, RecoveryForm, ChangePassForm
from werkzeug import secure_filename
from datetime import date
from Crypto.PublicKey import RSA
from Crypto.Cipher import AES
from misc import Pagination
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
# Default to Pillow and fallback to PIL
try: 
    import Image as PIL
except ImportError:
    import PIL

from models import db, User, UserType, Case, Key, Image, Database, Region
from crowd.models import TrainingImage

login_manager = LoginManager()
login_manager.init_app(app)

malariaList = ['Any Malaria Species','Falciparum','Vivax','Ovale','Malariae','No Malaria']

def get_admin():
    return UserType.query.filter(UserType.name == 'Administrator').first()

def get_doctor():
    return UserType.query.filter(UserType.name == 'Doctor').first()

def get_microscopist():
    return UserType.query.filter(UserType.name == 'Microscopist').first()

"""Allows only UserTypes in list parameter."""
def allowed(types=[]):
    def decorator(function):
        @wraps(function)
        def returned(*args, **kwargs):
            other = [i() for i in types]
            if current_user.usertype in other:
                return function(*args, **kwargs)
            else:
                abort(401)
        return returned
    return decorator

@app.route('/')
@app.route('/index/')
def index():
    if current_user.is_authenticated():
        return redirect('/dashboard/')
    return render_template("index.html",login_form = LoginForm(), recovery_form = RecoveryForm())
    
@app.route('/profilepage/', methods = ['GET', 'POST'])
@login_required
def profilepage():
    changepass_form = ChangePassForm()
    # Get old password, compare with form and change password
    if changepass_form.validate_on_submit():
        old_pass = changepass_form.oldpassword.data
        new_pass = changepass_form.newpassword.data
        changepass_form.oldpassword.data = changepass_form.newpassword.data = ""
        if old_pass == current_user.password:
            current_user.password = new_pass
            db.session.commit()
            message = 'Password successfuly changed.'
            return render_template("profilepage.html", user = current_user, changepass_form = changepass_form, message = message)
        # Error message if old password mismatches    
        error = 'Old password mismatch.'
        return render_template("profilepage.html", user = current_user, changepass_form = changepass_form, error = error)

    return render_template("profilepage.html", user = current_user, changepass_form = changepass_form)

@app.route('/dashboard/')
@login_required
def dashboard():
    # Tabular summaries of malaria distribution
    casenum=[]
    casenum2=[]
    percent1=[]
    percent2=[]
    regionList= Region.query.all()
    total = len(Case.query.all())
    for i in regionList:
        print i
        a=Case.query.filter(Case.region==i)
        a= [i for i in a] 
        casenum.append(len(a))
        temp= str((float(len(a))/float(total))*100)
        percent1.append(temp[:5] + '%')
    cases=zip(regionList,casenum,percent1)
    print 'cases:', len(cases), cases
    for i in malariaList[1:]:
        a=Case.query.filter(Case.human_diagnosis == i)
        a= [i for i in a] 
        print len(a)
        casenum2.append(len(a))
        temp= str((float(len(a))/float(total))*100)
        percent2.append(temp[:5] + '%')
    infsum=sum(casenum2)- casenum2[len(casenum2)-1]
    infperc=str((float(infsum)/float(total)) *100)[:5] + '%'
    cases2=zip(malariaList[1:],casenum2,percent2)
    return render_template("dashboard.html", user = current_user, cases=cases, cases2=cases2, malariaList = malariaList[1:], regionList = regionList[1:], date=datetime.datetime.now().strftime('%B %d, %Y'), casenum=casenum, total=total, percent1=percent1, percent2=percent2 ,infsum=infsum, infperc=infperc)

@app.route('/records/')
@login_required
def records():
    print request.args.get('page')
    if not request.args.get('page'):
        page = 1
    else:
        page = int(request.args.get('page'))
    # Malaria Case Filters
    # print request.args.get('malaria_selection') + request.args.get('region_selection') + request.args.get('date_start') + request.args.get('date_end')
    # Table sorter
    # print request.args.get('sort_by') # date, location, diagnosis
    # print request.args.get('order') # asc, desc
    regionList = ['All Regions']
    provinceList = ['All Provinces', 'kirong']
    cityList = ['All Cities', 'aldric']
    barangayList = ['All Barangays', 'noel']
    
    if request.args:
        malariaSelected = request.args.get('malaria_selection')
        regionSelected = request.args.get('region_selection')
        malariaIndex = malariaList.index(malariaSelected)
        regionList += [str(i) for i in Region.query.all()]
        regionIndex = regionList.index(regionSelected)
        
        date_start = request.args.get('date_start')
        date_end = request.args.get('date_end')
        sort_by = request.args.get('sort_by')
        order = request.args.get('order')
        
        caseList=''
        if date_start != 'The Beginning' :
            a=request.args.get('date_start')
            b=a.split('/')
            dt=datetime.date(int(b[2]),int(b[0]),int(b[1]))
            a=request.args.get('date_end')
            b=a.split('/')
            dte=datetime.date(int(b[2]),int(b[0]),int(b[1])) + datetime.timedelta(days=1)
        else :
            dt=datetime.date(1000,1,1)
            dte=datetime.date(9000,12,31)
            
        sortby=''
        if sort_by== 'date':
            sortby='date'
        elif sort_by== 'location':
            sortby='address'
        elif sort_by== 'diagnosis':
            sortby='human_diagnosis'
        else:
            sortby='id'
        param= "\"case\"."+sortby+" "+order
        print param
        if regionIndex == 0 and malariaIndex == 0: # Display all
            caseList= Case.query.filter(Case.date>=dt,Case.date<=dte).order_by(param)
        elif regionIndex == 0: # Whole Philippines
            caseList = Case.query.filter(Case.human_diagnosis == malariaSelected,Case.date>=dt,Case.date<=dte).order_by(param)       
        elif malariaIndex == 0: # Any malaria
            caseList = Case.query.filter(Case.region == Region.query.filter(Region.name == regionSelected).first(),Case.date>=dt,Case.date<=dte).order_by(param)
        else:
            caseList = Case.query.filter(Case.region == Region.query.filter(Region.name == regionSelected).first(),Case.human_diagnosis == malariaSelected,Case.date>=dt,Case.date<=dte).order_by(param)
    else:
        # Default values
        malariaIndex = 0
        regionIndex = 0
        date_start = "The Beginning"
        date_end = "This Day"
        sort_by = "date"
        order = "desc"
        caseList = Case.query.order_by(Case.date.desc())
    # filter allowed records to view if not admin or doctor   
    if (str(current_user.usertype)=='Microscopist'):
        templist=[]
        for i in caseList:
            if(i.user == current_user):
                templist.append(i)
        caseList=templist
    # Pagination
    caseList = [i for i in caseList]
    pagination = Pagination(page, Pagination.PER_PAGE, len(caseList))
    caseList = caseList[(page-1)*Pagination.PER_PAGE : ((page-1)*Pagination.PER_PAGE) + Pagination.PER_PAGE]
    
    regionList += [i for i in Region.query.all()]
    
    return render_template("records.html", caseList = caseList, pagination = pagination, malariaList = malariaList, regionList = regionList, malariaIndex = malariaIndex, regionIndex = regionIndex, date_start = date_start, date_end = date_end, sort_by = sort_by, order = order, user = current_user, provinceList=provinceList, cityList=cityList, barangayList=barangayList)

    
@app.route('/map/')
@login_required
def maps():
    # Filter arguments
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    zoom = request.args.get('zoom')
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    default_view = False
    # Check if filters exist
    if not (zoom and date_start and date_end):
        # Go to default view
        default_view = True
        date_start = 'Last 30 Days'
        date_end = 'Today'
        zoom = 7
        # return redirect('/map/?lat=10.422988&lng=120.629883&zoom=7&date_start=Last 30 Days&date_end=Today')
    # Build marker list for map
    dt=datetime.date.today()-datetime.timedelta(days=30)
    dte=datetime.date.today() + datetime.timedelta(days=1)
    if date_start != 'Last 30 Days' :
            a=request.args.get('date_start')
            b=a.split('/')
            dt=datetime.date(int(b[2]),int(b[0]),int(b[1]))
    if date_end != 'Today' :
            a=request.args.get('date_end')
            b=a.split('/')
            dte=datetime.date(int(b[2]),int(b[0]),int(b[1])) + datetime.timedelta(days=1)
    
    case_list = Case.query.filter(Case.date>=dt,Case.date<=dte)
    case_list = [i for i in case_list]
    sorted_list = dict([(i, []) for i in malariaList[1:]])
    for i in case_list:
        sorted_list[i.human_diagnosis].append(str(i.lat)+','+str(i.lng))
    
    if default_view or not(lat and lng):
        # Get centroid of markers of cases
        max_y = max_x = 0
        min_y = min_x = 9999
        for i in case_list:
            if i.lat > max_y:
                max_y = i.lat
            if i.lng > max_x:
                max_x = i.lng
            if i.lat < min_y:
                min_y = i.lat
            if i.lng < min_x:
                min_x = i.lng
        # Center
        lat = (min_y + max_y)/2
        lng = (min_x + max_x)/2
        # Calculate zoom based on resolution
        # TODO: Move to client side javascript if applicable
        try:
            zoom = math.floor(math.log(480 * 360 / (((max_y - min_y)+(max_x - min_x))/2) / 256) / 0.6931471805599453) - 1;
        except Exception, e:
            # Default zoom
            zoom = 7
            lat = 10.422988
            lng = 120.629883
    return render_template("map.html", lat = lat, lng = lng, zoom = zoom, case_list = sorted_list, date_start = date_start, date_end = date_end, user = current_user)
    
@app.route('/timeline/')
@login_required
def timeline():
    # Filter arguments
    lat = request.args.get('lat')
    lng = request.args.get('lng')
    zoom = request.args.get('zoom')
    date_start = request.args.get('date_start')
    date_end = request.args.get('date_end')
    default_view = False
    # Check if filters exist
    if not (zoom and date_start and date_end):
        # Go to default view
        default_view = True
        date_start = datetime.date.today()-datetime.timedelta(days=30)
        date_end = datetime.date.today()
        zoom = 7
        # return redirect('/map/?lat=10.422988&lng=120.629883&zoom=7&date_start=Last 30 Days&date_end=Today')
    # Build marker list for map
    
    case_list = Case.query.all()
    case_list = [i for i in case_list]
    
    min_date = case_list[0].date
    max_date = case_list[0].date
    
    sorted_list = dict([(i, []) for i in malariaList[1:]])
    for i in case_list:
        sorted_list[i.human_diagnosis].append((str(i.lat)+','+str(i.lng),i.date))
        
        if i.date > max_date:
            max_date = i.date
        if i.date < min_date:
            min_date = i.date
    
    date_start = str(min_date.year) + '-' + str(min_date.month) + '-' + str(min_date.day)
    date_end = str(max_date.year) + '-' + str(max_date.month) + '-' + str(max_date.day)
    
    date_start = min_date
    date_end = max_date
    
    if default_view or not(lat and lng):
        # Get centroid of markers of cases
        max_y = max_x = 0
        min_y = min_x = 9999
        for i in case_list:
            if i.lat > max_y:
                max_y = i.lat
            if i.lng > max_x:
                max_x = i.lng
            if i.lat < min_y:
                min_y = i.lat
            if i.lng < min_x:
                min_x = i.lng
        # Center
        lat = (min_y + max_y)/2
        lng = (min_x + max_x)/2
        # Calculate zoom based on resolution
        # TODO: Move to client side javascript if applicable
        try:
            zoom = math.floor(math.log(480 * 360 / (((max_y - min_y)+(max_x - min_x))/2) / 256) / 0.6931471805599453);
        except Exception, e:
            # Default zoom
            zoom = 7
            lat = 10.422988
            lng = 120.629883
    return render_template("timeline.html", lat = lat, lng = lng, zoom = zoom, case_list = sorted_list, date_start = date_start, date_end = date_end, user = current_user)

@app.route('/case/<int:id>/',  methods = ['GET', 'POST'])
def case(id):
    # Get case and corresponding images
    case = Case.query.get(id)
    images = []
    for img in case.images:
        images.append('pic/' + str(img.id))
    images = sorted(images)
    # Print out of case
    if request.method == 'POST':
        c = canvas.Canvas('malaria.pdf', pagesize=letter)
        width, height = letter
        reportString = 'Patient ID: ' + str(case.id) + '<br>' + 'Date: ' + case.date.strftime('%B %d, %Y') + '<br>' + 'Age: ' + str(case.age) + '<br>' + 'Address: ' + case.address + '<br>' + 'Diagnosis: ' + case.human_diagnosis + '<br>'
    
        x = reportString.split('<br>')
        for i, s in enumerate(x):
            c.drawString(100, 750 - i * 15, s)
        c.drawString(459, 750, '1')
        c.showPage()

        counter = 0
        page = 2
        print 'images:', images
        if request.form:
            for i in range (0, len(images)):
                if str('checkbox_' + str(i)) in request.form:
                    id = str(images[i]).split('/')[1]
                    x = Image.query.get(id).im
                    with open('image%s.jpg' % id,'w') as f:
                        f.write(x)
                    im = PIL.open('image%s.jpg' % id)
                    im2 = im.resize((200, 200), PIL.NEAREST).rotate(-90)
                    im2.save('image%s.jpg' % id)
                    c.drawImage('image%s.jpg' % id, 100, 500 - counter * 300)
                    counter += 1
                    if counter == 1:
                        c.drawString(459, 750, str(page))
                if counter == 2:
                    counter = 0
                    page += 1
                    c.showPage()
        c.save()
        with open('malaria.pdf','r') as f:
            pdf = f.read()
        response = make_response(pdf)
        response.headers["Content-Disposition"] = "attachment; filename=malaria.pdf"
        return response
    return render_template("case.html", case = case, user = current_user, images=images)

@app.route('/logout/')
def logout():
    logout_user()
    return redirect("index")
    
@login_manager.user_loader
def load_user(userid):
    return User.query.get(userid)

@app.route('/recovery/',  methods = ['GET', 'POST'])
def recovery():
    form = LoginForm()
    error = False
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username,password=password).first()
        if user:
            login_user(user)
            return redirect("/dashboard")
        else:
            return redirect("/index")
    else:
        error = True
        
    return redirect("/index")
   
@app.route('/login/',  methods = ['GET', 'POST'])
def login():
    form = LoginForm()
    error = False
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        user = User.query.filter_by(username=username,password=password).first()
        if user:
            login_user(user)
            return redirect("/dashboard")
        else:
            error = True
            error_message = "Invalid username or password!"
            return render_template("index.html",login_form = LoginForm(), recovery_form = RecoveryForm(), error_message = error_message)
    else:
        error = True
    return redirect("/index")

"""Returns a CSV file of the cases stored."""
@app.route('/csv/', methods = ['GET'])
@allowed([get_admin, get_doctor])
def csv():
    x = ['date,age,address,human diagnosis,latitude,longitude,malaria type,region']
    for case in Case.query.all():
        y = [case.date, case.age, case.address, case.human_diagnosis, case.lat, case.lng, case.maltype, case.region]
        y = map(str, y)
        x.append(','.join(y))
    csv = '\n'.join(x)
    response = make_response(csv)
    response.headers["Content-Disposition"] = "attachment; filename=malaria.csv"
    return response


# API

UPLOAD_FOLDER = os.path.join(os.getcwd().replace('\\','/'), 'upload/')
REMOVE_TEMP = False
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
upload_cache = {}

"""Decrypts the encrypted archive, stores the data if authenticated, and returns OK if successful."""
@app.route('/api/send/', methods=['GET','POST'])
def upload_file():
    if request.method == 'POST':
        # get file from form
        f = request.files['file']
        # if form is not empty
        if f:
            # temporarily save uploaded archive in folder with same name as archive filename
            filename = secure_filename(f.filename)
            folder = (app.config['UPLOAD_FOLDER'] + filename).replace('.zip', '')
            os.makedirs(folder)
            f.save(os.path.join(folder, filename))

            # extract uploaded archive to folder and delete original archive
            with open(os.path.join(folder, filename), 'r') as f:
                z = zipfile.ZipFile(f)
                z.extractall(folder)
            if REMOVE_TEMP:
                os.remove(f.name)

            # get encrypted AES key (128-bit SHA-1 of plaintext password) from XML file and decrypt using RSA private key
            with open(os.path.join(folder, 'accountData.xml'), 'r') as f:
                g = f.read()

            root = ET.fromstring(g)
            username = root.find('user').text
            enc_aes_key = root.find('pass').text.replace('\n','')
            enc_aes_key = base64.b64decode(enc_aes_key)
            private_key = RSA.importKey(Key.query.first().private_key)
            aes_key = private_key.decrypt(enc_aes_key)

            # decrypt image archive using decrypted AES key
            with open(os.path.join(folder, 'cipherZipFile.zip'), 'r') as f:
                enc_img_zip = f.read()
                cipher = AES.new(aes_key, AES.MODE_ECB, 'dummy_parameter')
                msg = cipher.decrypt(enc_img_zip)

            # store decrypted image archive on disk
            with open(os.path.join(folder, 'decrypted.zip'), 'w') as f:
                f.write(msg)
            if REMOVE_TEMP:
                os.remove(os.path.join(folder, 'cipherZipFile.zip'))

            # extract decrypted image archive and store in database
            with open(os.path.join(folder, 'decrypted.zip'), 'r') as f:
                z = zipfile.ZipFile(f)
                z.extractall(folder)
            if REMOVE_TEMP:
                os.remove(f.name)

            # make case using XML data
            tree = ET.parse(os.path.join(folder, 'textData.xml'))
            root = tree.getroot()
            mapping = {}
            for child in root:
                mapping[child.tag] = child.text
            month, day, year = map(int, mapping['date-created'].split('/'))
            hours, minutes, seconds = map(int, mapping['time-created'].split(':'))
            latitude = float(mapping['latitude'])
            longitude = float(mapping['longitude'])
            species = mapping['species'].replace('Plasmodium ', '').capitalize()
            age = mapping['age']
            address = mapping['address']
            region = Region.query.filter(Region.name == mapping['region']).first()

            dt = datetime.datetime(year, month, day, hours, minutes, seconds)
            case = Case(date=dt,age=age,address=address,human_diagnosis=species,lat=latitude,lng=longitude)
            case.region = region

            user = User.query.filter(User.username == username).first()
            hex_aes_key = ''.join(x.encode('hex') for x in aes_key)
            if hex_aes_key == user.password[:32]:
                db.session.add(case)
                db.session.commit()

                # store images in database
                for img_file in glob.glob(os.path.join(folder, "*.jpg")):
                    img = Image()
                    img.create_image(img_file, case)
                    db.session.add(img)
                    db.session.commit()
                    
                    # make new training image
                    trainingImg = TrainingImage(img.id, 0, 'Unlabeled', 'Unlabeled', None)
                    db.session.add(trainingImg)
                    db.session.commit()

                return 'OK'
            else:
                # {'username': (tries, case, folder)
                upload_cache[username] = (0, case, folder)
                return 'RETYPE 0'


    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

"""Handles retyping of passwords from app."""
@app.route('/api/retype/', methods=['GET','POST'])
def retype():
    if request.method == 'POST':
        x = request.form['message'].split('\n')
        username = x[0]
        aes_key = base64.b64decode(x[1])
        hex_aes_key = ''.join(x.encode('hex') for x in aes_key)

        print username
        user = User.query.filter(User.username == username).first()
        print '1', hex_aes_key == user.password[:32]
        print '2', hex_aes_key
        print '3', user.password[:32]

        print upload_cache
        entry = upload_cache.get(username)
        if not entry:
            return 'RETYPE 5'
        tries = entry[0]
        case = entry[1]
        folder = entry[2]
        if hex_aes_key == user.password[:32]:
            db.session.add(case)
            db.session.commit()

            # store images in database
            for img_file in glob.glob(os.path.join(folder, "*.jpg")):
                img = Image()
                img.create_image(img_file, case)
                db.session.add(img)
                db.session.commit()

            return 'OK'
        else:
            if tries != 4:
                upload_cache[username] = (tries + 1, case, folder)
            else:
                upload_cache.pop(username)
            return "RETYPE %s" % tries


"""Returns the RSA public key."""
@app.route('/api/key/', methods=['GET'])
def update_key():
    key = Key.query.first()
    public_key = key.public_key
    return public_key

"""Returns a Base-64 string of the credentials database, or "OK" otherwise."""
@app.route('/api/db/', methods=['GET','POST'])
def update_db():
    if request.method == 'GET':
        return '''
        <!doctype html>
        <title>Get database date</title>
        <h1>Get database date</h1>
        <form action="" method=post>
          <p><input type=text name=message>
             <input type=submit value=Send>
        </form>
        '''
    elif request.method == 'POST':
        date_string = request.form['message']
        # if sent date < modified date
        if Database.need_update(date_string):
            conn = sqlite3.connect('updated.db')
            c = conn.cursor()
            c.execute("DELETE FROM user")
            for user in User.query.all():
                username = user.username
                password = user.password
                c.execute("INSERT INTO user VALUES(NULL, '%s', '%s')" % (username, password))
            conn.commit()
            conn.close()
            with open('updated.db', 'r') as f:
                g = f.read()
            return base64.b64encode(g)
        else:
            return 'OK'

    """
    temp = []
    for entry in User.query.all():
        username = entry.username
        password = entry.password
        temp.append(username + ',' + password)
    return '\n'.join(temp)
    """

"""Returns the APK if the version string sent differs from the current, or "OK" otherwise."""
@app.route('/api/apk/', methods=['GET','POST'])
def update_apk():
    if request.method == 'POST':
        # assume server always has latest version
        if request.form['message'] != '1.0':
            return redirect(url_for('static', filename='Malaria-debug-unaligned.apk'))
        else:
            return 'OK'

"""Returns the JPG requested."""
@app.route('/pic/<int:picture_id>/', methods=['GET'])
def fetch_image(picture_id):
    x = Image.query.get(picture_id)
    response = make_response(x.im)
    response.headers['Content-Type'] = 'image/jpeg'
    return response
