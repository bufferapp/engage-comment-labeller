.DEFAULT_GOAL := run

IMAGE_NAME := gcr.io/buffer-data/engage-comment-labeller:0.2.0

GCLOUD_CONFIG_FLAG = -v $(HOME)/.config/gcloud/:/root/.config/gcloud

.PHONY: build
build:
	@docker build -t $(IMAGE_NAME) .

.PHONY: run
run: build
	@docker run --rm -it -p 8080:8080 --env-file=.env $(GCLOUD_CONFIG_FLAG) $(IMAGE_NAME)

.PHONY: dev
dev: build
	@docker run --rm -it -p 8080:8080 --env-file=.env $(GCLOUD_CONFIG_FLAG) $(IMAGE_NAME) /bin/bash

.PHONY: push
push: build
	@docker push $(IMAGE_NAME)

.PHONY: deploy
deploy: build
	@gcloud app deploy

