Запуск ngrok
D:\Install\ngrok\ngrok.exe http 5000

git push -u origin main

git add .
git commit -m "яна куп фильтрлар кушдим!"
heroku login
heroku container:login
heroku create farrosh-bot --stack=container
heroku container:push web -a farrosh-bot
heroku container:release web -a farrosh-bot





heroku logs --tail -a farrosh-bot