.PHONY: run test-ask start bash

REGION=eu-central-1
SAM=AWS_REGION=$(REGION) sam

run:
	AWS_DEFAULT_REGION=$(REGION) python3 qanda/main.py

test-answer:
	$(SAM) local invoke --skip-pull-image --env-vars invoke/env_vars.json -e invoke/answer_sms.json Flask

test-ask:
	$(SAM) local invoke --skip-pull-image --env-vars invoke/env_vars.json -e invoke/ask.json Flask

start:
	$(SAM) local start-api --env-vars invoke/env_vars.json Flask

bash:
	docker run -v $PWD:/var/task -it lambci/lambda:build-python3.6 /bin/bash
