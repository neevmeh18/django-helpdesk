(function () {
    $(function () {
        var panel = document.getElementById("public-ticket-status");
        if (!panel) {
            return;
        }

        var ticket = panel.getAttribute("data-ticket");
        var email = panel.getAttribute("data-email");
        var statusUrl = panel.getAttribute("data-status-url");
        if (!ticket || !email || !statusUrl) {
            return;
        }

        var params = new URLSearchParams();
        params.set("ticket", ticket);
        params.set("email", email);
        var requestUrl = statusUrl + "?" + params.toString();

        function updateText(id, value) {
            var el = document.getElementById(id);
            if (!el || value == null) {
                return;
            }
            el.textContent = value;
        }

        function poll() {
            fetch(requestUrl)
                .then(function (response) {
                    if (!response.ok) {
                        throw new Error();
                    }
                    return response.json();
                })
                .then(function (data) {
                    updateText("pts-status", data.status);
                    updateText(
                        "pts-queue",
                        data.queue && data.queue.title
                    );
                    updateText("pts-due", data.due_date);
                })
                .catch(function () {
                    clearInterval(timer);
                });
        }

        var timer = setInterval(poll, 60000);
    });
})();
