# Ramibarmja<!DOCTYPE html>
<html>
<head>
    <title>موقعي البسيط</title>
    <style>
        body { font-family: Arial; text-align: center; margin-top: 50px; }
        button { padding: 10px 20px; font-size: 16px; }
    </style>
</head>
<body>
    <h1 id="title">مرحبا بك في موقعي!</h1>
    <button onclick="changeText()">اضغط هنا</button>

    <script>
        function changeText() {
            document.getElementById('title').innerText = "شكراً للضغط!";
        }
    </script>
</body>
</html>
