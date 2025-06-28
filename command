Запуск ngrok
D:\Install\ngrok\ngrok.exe http 5000

git add .
git commit -m "яна куп фильтрлар кушдим!"

heroku container:login
heroku container:push web -a farrosh-bot
heroku container:release web -a farrosh-bot


git push -u origin main



heroku logs --tail