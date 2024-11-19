document.addEventListener("DOMContentLoaded", function() {
    const cont = document.getElementById("buttons")

    fetch('/get_sessions')
    .then(response => response.json())
    .then(data =>{
        sessions = data.list;
        console.log(sessions);
        if (sessions.length === 0) {
            document.getElementById('sessions').innerHTML = "<p>Non ci sono sessioni concluse</p>";
        } else {
            sessions.forEach(session => {
                const [x, id] = session;

                const button = document.createElement('button');
                button.className = 'btn-session';
                button.id = id+"_"+x;
                button.innerText = "Sessione "+x;
                button.classList.add("btn","btn-primary","mx-2","my-2");
                cont.appendChild(button);

                button.addEventListener("click", function(){
                    window.location.href = "/download_csv/"+this.id;
                });

            });
        };
    })
    .catch(error => console.error('Error loading data : ', error));
});