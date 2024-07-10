
fetch('/get_sessions')
    .then(response => response.json())
    .then(data =>{
        sessions = data.sessions;
        console.log(sessions)
        if (sessions.length === 0) {
            document.getElementById('sessions').innerHTML = "<p>Non ci sono sessioni concluse</p>";
        } else {
            // Loop through the sessions array
            for (var i = 0; i < sessions.length; i++) {
                var session = sessions[i]; // Get the current session object

                // Create a button for each session
                var button = document.createElement("button");
                button.setAttribute('type', 'button');
                button.setAttribute('id','session-'+session['number']);
                button.setAttribute('class', 'btn btn-primary mx-1 inline-block btn-session');
                button.innerText = session['number']; // Assuming session is a string or some value you want to display
                document.getElementById("buttons").appendChild(button);
                
                var result = document.createElement("div");
                result.setAttribute("class","d-none");
                result.setAttribute("id",'session-'+session['number']+'-text');
                result.innerHTML = '<p>'+session['result']+'</p>';
                document.getElementById('sessions-text-hidden').appendChild(result);
            
            
            }

            const buttons = document.querySelectorAll('.btn-session');
            buttons.forEach(btn => {
                btn.addEventListener('click',function(){
                    document.getElementById('sessions-text').innerText = document.getElementById(btn.id+'-text').innerText;
                })
            })
        };
    })
    .catch(error => console.error('Error loading data : ', error));