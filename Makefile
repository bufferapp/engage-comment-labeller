.DEFAULT_GOAL := run

IMAGE_NAME := gcr.io/buffer-data/engage-comment-labeller:0.1.0

GCLOUD_CONFIG_FLAG = -v $(HOME)/.config/gcloud/:/root/.config/gcloud

.PHONY: build
build:
	@docker build -t $(IMAGE_NAME) .

.PHONY: run
run: build
	@docker run --rm -it -p 8501:8501 --env-file=.env $(GCLOUD_CONFIG_FLAG) $(IMAGE_NAME)

.PHONY: dev
dev: build
	@docker run --rm -it -p 8501:8501 --env-file=.env $(GCLOUD_CONFIG_FLAG) $(IMAGE_NAME) /bin/bash

.PHONY: build
push: build
	@docker push $(IMAGE_NAME)
