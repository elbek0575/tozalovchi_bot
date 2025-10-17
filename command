Запуск ngrok
D:\Install\ngrok\ngrok.exe http 5000

git push -u origin main

git add .
git commit -m "Кушимча (/ins) буйруклар кииритилди"
git push heroku main


heroku container:push web -a farrosh-bot
heroku container:release web -a farrosh-bot
heroku logs --tail

heroku login
heroku container:login


heroku logs --tail -a farrosh-bot



heroku ps -a farrosh-bot

heroku ps:scale worker=0 -a farrosh-bot

heroku ps:scale web=1 -a farrosh-bot

set HEROKU_API_KEY=

heroku login