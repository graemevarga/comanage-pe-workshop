# Optional shortcuts; each target is a plain docker compose command you can also type yourself.
COMPOSE   := docker compose
BUILD     := $(COMPOSE) -f compose.yaml -f compose.build.yaml
AUTHOR    := $(COMPOSE) -f compose.yaml -f compose.author.yaml
IMAGE     ?= ghcr.io/graemevarga/comanage-pe-workshop:5.2.0-1
PLATFORMS ?= linux/amd64,linux/arm64

.PHONY: help up down logs shell status list restore reset checkpoint cake build author build-arm64 push

help:
	@echo "Participants: make up | down | logs | status | list | restore NAME=04-filesource-synced | reset | shell"
	@echo "Instructors:  make author | checkpoint NAME=... DESC=\"...\" | cake ARGS=\"...\""
	@echo "Maintainers:  make build | build-arm64 | push"

up:
	$(COMPOSE) up -d
down:
	$(COMPOSE) down
logs:
	$(COMPOSE) logs -f registry
shell:
	$(COMPOSE) exec registry bash
status:
	$(COMPOSE) exec registry workshop status
list:
	$(COMPOSE) exec registry workshop list
restore:
	$(COMPOSE) exec registry workshop restore $(NAME)
reset:
	$(COMPOSE) exec registry workshop reset
checkpoint:
	$(COMPOSE) exec registry workshop checkpoint $(NAME) $(DESC)
cake:
	$(COMPOSE) exec registry workshop cake $(ARGS)

build:
	$(BUILD) build
author:
	$(BUILD) -f compose.author.yaml up -d
build-arm64:
	docker buildx build --platform linux/arm64 --load -t comanage-pe-workshop:arm64 ./image
push:
	docker buildx build --platform $(PLATFORMS) -t $(IMAGE) --push ./image
