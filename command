Запуск ngrok
D:\Install\ngrok\ngrok.exe http 5000

git add .
git commit -m "яна куп фильтрлар кушдим!"
# Docker registry'га логин
heroku container:login

# Контейнерни Heroku'га пуш қилиш
heroku container:push web -a farrosh-bot

# Контейнерни ишга тушириш
heroku container:release web -a farrosh-bot


git push -u origin main



heroku logs --tail