test-ask:
	sam local invoke --env-vars invoke/env_vars.json -e invoke/ask.json Flask

start:
	sam local start-api --env-vars invoke/env_vars.json Flask

bash:
	docker run -v $PWD:/var/task -it lambci/lambda:build-python3.6 /bin/bash
