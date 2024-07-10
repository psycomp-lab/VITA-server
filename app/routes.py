from app import app
from flask import request,redirect,url_for,flash,session,render_template
import re
import json
from datetime import date,datetime
from app.models import db,User,Session,Training,Exercise,TrainingExercise
from app.form import Registration,New_Workout
from app.utils import serialize_list,get_exercises
from app.socket_udp import client_ips,send_connect,is_connected,send_data

"""
#Funzione usata da Fetch per riprendere le vecchie sessioni (da testare)
@app.route("/get_sessions")
def get_sessions():
    sessions = Session.query.filter(Session.result.isnot(None)).all()
    sessions_list = serialize_list(sessions)
    for item in sessions_list:
        if isinstance(item["result"], bytes):
            item["result"] = item["result"].decode()
    print(sessions_list)
    return jsonify({"sessions": sessions_list})"""


@app.route("/")
def welcome():
    return render_template("welcome.html")

@app.route("/connect-vr",methods=["GET","POST"])
def connection():
    if request.method == "POST":
        ip = int(request.form.get("client"))
        #SEND CONNECT MESSAGE TO CLIENT, SET CONNECTED TO TRUE AND START COMMUNICATION
        try:
            send_connect(client_ips[ip])
        except Exception as e:
            print(f"Error while connecting: {e}")
        if is_connected():
            client_ips.clear()
            return redirect(url_for("search_user"))
        else:
            flash("Errore nella connessione riprovare","error")
            return redirect(request.url)
    return render_template("choose_vr.html",clients_ip = client_ips)

@app.route("/search-user",methods=["GET","POST"])
def search_user():
    if is_connected():
        if request.method == "POST":
            search = request.form.get("codice")
            if not search:
                flash("Inserisci il codice utente.", "error")
                return redirect(request.url)
            
            if not re.match("^[0-9]*$", search):
                flash("Il codice deve essere composto solo da numeri.", "error")
                return redirect(request.url)

            try:
                user = User.query.filter_by(code=search).first()
            except Exception as e:
                app.logger.error(f"Error searching user: {e}")
                flash("Si è verificato un errore nella ricerca dell'utente.", "error")
                return redirect(request.url)

            if not user:
                link = url_for("form")
                flash(f"Il codice inserito non è registrato. Per registrare l\"utente vai al seguente <a href=\"{link}\">LINK</a>", "info")
                return redirect(request.url)

            app.logger.info("User found")
            session["code"] = user.code
            return redirect(url_for("info"))

        return render_template("home.html")
    else:
        flash("Devi connetterti al visore","disconnected")
        return render_template("home.html")

@app.route("/form",methods=["GET","POST"])
def form():
    form = Registration()
    if form.validate_on_submit():
        try:
            # Form values for the registration
            name = request.form.get("name").capitalize()
            surname = request.form.get("surname").capitalize()
            code = request.form.get("code")
            sex = request.form.get("sex")
            dob = datetime.strptime(request.form.get("dob"), "%Y-%m-%d")
            info1 = request.form.get("info1").capitalize()
            info2 = request.form.get("info2").capitalize()

            # Create user object
            new_user = User(name=name, surname=surname, code=code, dob=dob, sex=sex, info1=info1, info2=info2)
            db.session.add(new_user)

            """ Create new session
            new_session = Session(user_id=code)
            db.session.add(new_session)"""

            db.session.commit()
            app.logger.info("Created new user.")
        except Exception as e:
            app.logger.error(f"Error in form(): {e}")
            return redirect("/form")

        # Initialize session code
        session["code"] = code
        return redirect(url_for("info"))
    return render_template("form.html", form=form)

@app.route("/user",methods=["GET","POST"])
def info():
    code = session.get("code")
    if code and is_connected():
        # Get user info
        row = User.query.filter_by(code=code).first()
        app.logger.info("Found user's info")
        
        if request.method == "POST":
            try:
                if "form1-submit" in request.form:
                    modifica1 = request.form.get("modifica1").capitalize()
                    row.info1 = modifica1
                elif "form2-submit" in request.form:
                    modifica2 = request.form.get("modifica2").capitalize()
                    row.info2 = modifica2
                db.session.commit()
                app.logger.info("User info modified")
                return redirect(request.url)
            except Exception as e:
                app.logger.error(f"Error in info(): {e}")
                return redirect(request.url)
        return render_template("info.html", row=row, year=date.today())
    else:
        return redirect(url_for("search_user"))


@app.route("/session",methods=["GET","POST"])
def choose_workout():
    code = session.get("code")
    if code and is_connected():

        workouts = {}
        n_trainings = Training.query.count()
        
        # Get all the trainings
        for n in range(1, n_trainings + 1):
            names = []  # List of exercises" names
            training = Training.query.get(n)  # Training
            exercises = TrainingExercise.query.filter_by(training_id=training.id).all()  # Exercises in training
            for ex in exercises:
                exercise = Exercise.query.get(ex.exercise_id)
                if exercise:
                    names.append(exercise.name)
            workouts[training.name] = names
        
        sessions = Session.query.filter_by(user_id=code).order_by(Session.number.desc()).all()

        if not sessions:
            n_session = 1
        else:
            highest_session = sessions[0]
            n_session = highest_session.number

            for s in sessions:
                if s.result is None:
                    flash("Unfished session","session_alert")
            n_session += 1

        app.logger.info("Accessed DB")
        
        
        if request.method == "POST":
            # Handle the POST request
            exercises_list = serialize_list(get_exercises(request.form.get("workout")))
            for ex in exercises_list:
                new_session = Session(code, n_session, ex["id"])
                db.session.add(new_session)
            db.session.commit()
            #data = {"id":code,"list_exercises":exercises_list}
            # Maurizio-start
            data = {"id": code, "list_exercises": exercises_list, "session_number" : n_session} # added session number
            # Maurizio-end
            session["data"] = data

            return redirect(url_for("session_start"))
        
        # Render the template for the GET request
        return render_template("choose_workout.html", workouts=workouts, n_session=n_session)
    else:
        flash("Devi connetterti al visore", "disconnected")
        return redirect(request.url)
    

@app.route("/user/create_workout",methods=["GET","POST"])
def new_training():
    code = session.get("code")
    if code and is_connected():        
        exs = New_Workout()
        if exs.validate_on_submit():
            exercises = []
            for i in range(1, 6):  # Assuming you have 5 exercises
                exercise_id = request.form.get(f"ex{i}")
                exercise = Exercise.query.get(exercise_id)
                if exercise:
                    exercises.append(exercise.serialize())
            # Maurizio-start
            data = {"id": code, "list_exercises": exercises, "session_number" : 1} # added session number
            # Maurizio-end
            session["data"] = data    
            return redirect(url_for("session_start"))
        else:
            return render_template("new_workout.html",form=exs)
    else:
        flash("Devi connetterti al visore", "disconnected")
        return redirect(request.url)

@app.route("/restart_session")
def restart_session():
    sessions = Session.query.filter_by(user_id=session["code"]).order_by(Session.number.desc()).all()
    for s in sessions:
        db.session.delete(s)
    db.session.commit()
    return redirect(url_for("choose_workout"))


@app.route("/continue_session")
def continue_session():
    
    user_code = session.get("code")  # Get the user code from the session
    highest_session = Session.query.filter_by(user_id=user_code).filter(Session.result.is_(None)).order_by(Session.number.desc()).first()
    
    if highest_session:
        # Get the session number
        n = highest_session.number
        
        # Find all exercises with the same session number
        exercises = Session.query.filter_by(user_id=user_code, number=n).all()
        
        serialized_exercises = []
        for ex in exercises:
            # Ensure you fetch the exercise details by its ID
            exercise = Exercise.query.get(ex.exercise)
            if exercise:
                serialized_exercises.append(exercise.serialize())
        
        data = {"id": user_code, "list_exercises": serialized_exercises, "session_number" : n}
        session["data"] = data  # Store only serializable data in the session
        return redirect(url_for("session_start"))
    else:
        return "No session found", 404



@app.route("/user/session")
def session_start():
    code = session["code"]
    if code and is_connected():
        vr_data = session.get("data")
        # Maurizio-start:
        #send vr dict data
        # send_data("SESSION", json.dumps(vr_data))
        #print(session)
        exercise_string = ""
        for exercise in session["data"]["list_exercises"]:
            exercise_string += str(exercise["id"]) + " "
        exercise_string = exercise_string[:-1]
        send_data("SESSION", code + " " + str(session["data"]["session_number"]) + " " + exercise_string)
        # Maurizio-end
        return render_template("session.html",user = vr_data["id"],data = vr_data["list_exercises"])
    else:
        flash("Devi connetterti al visore", "disconnected")
        return redirect(request.url)
    