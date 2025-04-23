# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Flask modules
from flask   import Flask, render_template, request, redirect, url_for, flash, session
from jinja2  import TemplateNotFound


# App modules
from app import app, db, cursor
# from app.models import Profiles

# Other inputs
from datetime import datetime

import csv, pandas, io

# App main route + generic routing
@app.route('/')
def index():
    if not session.get('student_id'):
        session["student_id"] = 'none'
        session["isLoggedIn"] = False

    if session["student_id"] == 'none':
        return redirect(url_for('login'))

    else:
        return redirect(url_for('student_dashboard', sid=session["student_id"])) if session['isProfessor'] == False else redirect(url_for('professorHome', pid=session["student_id"]))

    return render_template('peerevalform.html')

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/professorDashboard/<pid>')
def professorHome(pid):
    sql = "SELECT COUNT(DISTINCT Student.Student_ID) AS Count_Students_Enrolled, (SELECT COUNT(Course_ID) FROM Course WHERE Professor_ID = %s) AS Count_Courses_Taught FROM Student JOIN Student_Course ON Student.Student_ID = Student_Course.Student_ID JOIN Course ON Student_Course.Course_ID = Course.Course_ID WHERE Course.Professor_ID = %s;"
    cursor.execute(sql, [pid, pid])

    result = cursor.fetchone()

    sql = "SELECT Course.Course_ID, Course.CourseCode, Course.CourseName, COUNT(`Groups`.Group_ID) AS 'GroupCount' FROM Course LEFT JOIN `Groups` ON `Groups`.Course_ID = Course.Course_ID WHERE Course.Professor_ID = %s GROUP BY Course.Course_ID, Course.CourseCode, Course.CourseName;"
    cursor.execute(sql, [pid])

    courses=cursor.fetchall()


    sql = 'SELECT c.Course_ID, c.CourseCode, c.CourseName, CASE WHEN EXISTS (SELECT 1 FROM `Groups` g JOIN Peer_Evaluation pe ON pe.Group_ID = g.Group_ID WHERE g.Course_ID = c.Course_ID AND CURRENT_DATE BETWEEN pe.Start_Date AND pe.Due_Date) THEN 1 ELSE 0 END AS HasActiveEvaluation FROM Course c WHERE c.Professor_ID = %s;'
    cursor.execute(sql, [pid])

    evaluations = cursor.fetchall()

    return render_template('profdashboard.html', activeCourses=result['Count_Courses_Taught'], totalStudents=result['Count_Students_Enrolled'], courses=courses, evaluations=evaluations)



def checkProfessorRegister(email, pwd):

    sql = "select * from Professor where Email=%s and Password=%s;"
    cursor.execute(sql, [email, pwd])
    result = cursor.fetchone()

    if result is None:
        return False
    
    else:
        setUserInfo(result['Professor_ID'], result['FirstName'], result['LastName'], email, isProf=True)
        return result['Professor_ID']

@app.route('/userLogin', methods=["POST"])
def userLogin():

    email = request.form.get("email")
    pwd = request.form.get("password")

    sql = "select * from Student where Email=%s and Password=%s;"

    cursor.execute(sql, [email, pwd])
    result = cursor.fetchone()

    if result is None:
        isProfessor = checkProfessorRegister(email, pwd)


        return redirect(url_for('login')) if not isProfessor else redirect(url_for('professorHome', pid=isProfessor))
    else:
        setUserInfo(result["Student_ID"], result["FirstName"], result["LastName"], result["Email"], isProf=False)
        
        return redirect(url_for("student_dashboard", sid=session["student_id"]))

@app.route('/studentdashboard/<sid>')
def student_dashboard(sid):

    if not session.get('student_id') or session["student_id"] == 'none':
        return redirect(url_for('login'))
    
    else:

        sql = "SELECT c.CourseName, g.GroupName, pe.*, DATEDIFF(pe.Due_Date, CURDATE()) AS Days_Until_Due FROM Peer_Evaluation pe JOIN `Groups` g ON pe.Group_ID = g.Group_ID JOIN Course c ON g.Course_ID = c.Course_ID JOIN Student_Groups sg ON g.Group_ID = sg.Group_ID WHERE sg.Student_ID = %s;"

        cursor.execute(sql, [session["student_id"]])

        evalInfo = cursor.fetchall()    
        evalList = []

        #                                                                                   LOOK AT THIS STUFF ??????????????????????////

        for eval in evalInfo:
            eid = eval["Evaluation_ID"]
            sql = "select * from Evaluation_Result where Evaluation_ID=%s and Evaluator_ID=%s;"
            cursor.execute(sql, [eid, sid])   
            results = cursor.fetchall()
            if results is None:
                pass
            else:
                evalList.append(eval)


        return render_template('studentdashboard.html', sid=sid, evalLinks=evalList)

@app.route('/eval/<eid>/<gid>')
def eval(eid, gid):
    if not session.get('student_id') or session["student_id"] == 'none':
        return redirect(url_for('login'))
    
    else:
        sql = "SELECT s.Student_ID, s.FirstName, s.LastName, sg.Group_ID FROM Student s JOIN Student_Groups sg ON s.Student_ID = sg.Student_ID WHERE sg.Group_ID = %s AND s.Student_ID <> %s;"
        cursor.execute(sql, [gid, session["student_id"]])
        peeps = cursor.fetchall()

        return render_template('peerevalform.html', peeps=peeps, eid=eid)

@app.route('/submitPeerEvaluation/<eid>', methods=['POST'])
def submitEval(eid):
    # get the form results
    evaluated = int(request.form.get('evaluated'))
    evaluator = session["student_id"]
    date = datetime.now()
    intel_creativity = int(request.form.get('intelCreative'))
    interpersonal = int(request.form.get('interpersonal'))
    disciplinary = int(request.form.get('disciplinary'))
    citizenship = int(request.form.get('citizenship'))
    mastery = int(request.form.get('mastery'))
    comments = request.form.get('comments')

    # database connection setup
    # insert data into Evaluation_Result
    
    GLOs = [intel_creativity, interpersonal, disciplinary, citizenship, mastery]
    i = 0

    for score in GLOs:
        i += 1
        
        sql = '''
            INSERT INTO Evaluation_Result (Evaluation_ID, Evaluator_ID, Evaluated_ID, GLO_ID, Score, Date_Time, Course_ID) 
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        '''
        try:
            cursor.execute(sql, [eid, evaluator, evaluated, i, score, date, 1])
            db.commit()
        except Exception as e:
            print(f"An error occurred: {e}")
            db.rollback()        

    return redirect(url_for('student_dashboard', sid=session["student_id"]))


@app.route('/student-course-mgr', methods=['POST', 'GET'])
def student_course_mgr():
    data = []
    profClasses = "select Course_ID, CourseCode from Course where Professor_ID=%s;"
    cursor.execute(profClasses, [session['student_id']])
    classes = cursor.fetchall()
    
    if request.method == 'POST':
        uploaded_file = request.files['file']
        if uploaded_file and uploaded_file.filename.endswith('.csv'):
            stream = io.StringIO(uploaded_file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.reader(stream)
            next(csv_input, None)
            data = list(csv_input)
            session['tempdata'] = data

    return render_template('manager1.html', data=data, classes=classes)

@app.route('/post-batch-students', methods=['POST', 'GET'])
def postBatchStudents():

    # note that the session var data is going to come out as a list of lists(indexes = each cell data)
    course_id = request.form.get("classSelect")
    # print(session['tempdata'], id)

    for student in session['tempdata']:
        fname = student[0]
        lname = student[1]
        email = student[2]

        # SQL insert using this student info
        insertNewStudent(fname, lname, email)
        
        student_id = fetchStudentID(email)
        
        # SQL to assign student to course using 'id variable'

        addStudentToCourse(student_id, course_id)

    return redirect(url_for('index'))



def insertNewStudent(fname, lname, email):              # use this for new student

    sql = "insert into Student(FirstName, LastName, Email, Password, Date_Added) values(%s, %s, %s, 'default', current_date());"
    cursor.execute(sql, [fname, lname, email])
    db.commit()

def addStudentToCourse(student_id, course_id):
    sql = "insert into Student_Course(Student_ID, Course_ID) values(%s, %s);"
    cursor.execute(sql, [student_id, course_id])
    db.commit()

def fetchStudentID(email):

    student_id = "select Student_ID from Student where Email=%s;"
    cursor.execute(student_id, [email])
    student_id = cursor.fetchone()['Student_ID']

    return student_id


@app.route('/addStudentProfile', methods=['POST', 'GET'])
def addStudentProfile():
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    email = request.form.get('email')
    course_id = request.form.get('classSelect2')

    insertNewStudent(fname, lname, email)

    student_id = fetchStudentID(email)

    addStudentToCourse(student_id, course_id)

    return redirect(url_for('student_course_mgr'))                # change address with edit later


@app.route('/addCourse', methods=['POST', 'GET'])
def addCourse():
    ccode = request.form.get('ccode')
    cname = request.form.get('cname')
    semester = request.form.get('semester')
    year = request.form.get('year')
    time = request.form.get('time')

    sql = 'Insert into Course(CourseCode, CourseName, Professor_ID, Semester, Year, Time) VALUES(%s, %s, %s, %s, %s, %s)'
    cursor.execute(sql, [ccode, cname, session['student_id'], semester, year, time])
    db.commit()

    return redirect(url_for('student_course_mgr'))

@app.route('/loggingout')
def logout():
    session["student_id"] = None
    session["fname"] = None
    session["lname"] = None
    session['email'] = None
    session['isLoggedIn'] = False

    return redirect(url_for('login'))

@app.route('/student-group-mgr', methods=['POST', 'GET'])
def student_group_mgr():

    students = None    
    profClasses = "select Course_ID, CourseCode from Course where Professor_ID=%s;"
    cursor.execute(profClasses, [session['student_id']])
    classes = cursor.fetchall()

    course_id = request.form.get('classSelect2')

    if course_id != None:
        sql = 'select * from Student where Student_ID in (select Student_ID from Student_Course where Course_ID=%s);'
        cursor.execute(sql, [course_id])
        students = cursor.fetchall()
        session['tempdata'] = course_id
    
    return render_template('manager2.html', classes=classes, course_id=course_id, students=students)

@app.route('/createGroup', methods=['POST'])
def createGroup():
    course_id = session['tempdata']
    students = request.form.getlist('students')
    groupName = request.form.get('groupName')

    if len(students) > 0:
        sql = 'INSERT INTO `Groups`(Course_ID, GroupName) VALUES(%s, %s)'
        cursor.execute(sql, [course_id, groupName])
        db.commit()

        sql = 'SELECT Group_ID FROM `Groups` WHERE GroupName = %s'
        cursor.execute(sql, [groupName])
        groupID = cursor.fetchone()['Group_ID']

        for student in students:
            sql = 'INSERT INTO Student_Groups(Student_ID, Group_ID) VALUES(%s, %s)'
            cursor.execute(sql, [student, groupID])
            db.commit()
    else:
        return redirect(url_for('student_group_mgr'))

    return redirect(url_for('index'))


#########################################################################
# Schedule Peer Evaluations
@app.route('/peer-evaluation-mgr', methods=['POST', 'GET'])
def evaluationScheduler():

    groups = None    
    profClasses = "select Course_ID, CourseCode from Course where Professor_ID=%s;"
    cursor.execute(profClasses, [session['student_id']])
    classes = cursor.fetchall()

    course_id = request.form.get('classSelect2')

    if course_id != None:
        sql = 'Select * from `Groups` where Course_ID = %s;'
        cursor.execute(sql, [course_id])
        groups = cursor.fetchall()
        session['tempdata'] = course_id
    
    return render_template('scheduleevaluations.html', groups=groups, classes=classes, course_id=course_id)

@app.route('/scheduleEval', methods=['POST', 'GET'])
def scheduleEval():
    groups = request.form.getlist('groups')
    start_date = request.form.get('start_date')
    due_date = request.form.get('due_date')

    if len(groups) == 0:
        return redirect(url_for('evaluationScheduler'))
    
    if not start_date:
        return redirect(url_for('evaluationScheduler'))

    if not due_date:
        return redirect(url_for('evaluationScheduler'))

    for group in groups:
        sql = 'INSERT INTO Peer_Evaluation(Group_ID, Start_Date, Due_Date) VALUES(%s, %s, %s)'
        cursor.execute(sql, [group, start_date, due_date])
        db.commit()

    return redirect(url_for('index'))


def setUserInfo(id, fname, lname, email, isProf):
    session["student_id"] = id
    session["fname"] = fname
    session["lname"] = lname
    session['email'] = email
    session['isLoggedIn'] = True
    session['isProfessor'] = isProf

def stopDatabase():
    cursor.close()
    db.close()