up:
	docker-compose up -d
exec:
	docker container exec -it chat_app  /bin/bash
down:
	docker-compose down
stop:
	docker-compose stop