# Makefile for monorepo with independent services

# Service directories
BET_MAKER_DIR := bet_maker
LINE_PROVIDER_DIR := line_provider
MESSAGE_BROKER_DIR := message_broker

# Docker-compose commands
DC_UP = docker-compose up -d
DC_DOWN = docker-compose down
DC_REBUILD = docker-compose up -d --build
DC_PS = docker-compose ps
DC_CLEAN = docker-compose down -v --rmi local
SLEEP = sleep 10

.PHONY: all up down rebuild ps clean \
        up-bet-maker up-line-provider up-message-broker \
        down-bet-maker down-line-provider down-message-broker \
        rebuild-bet-maker rebuild-line-provider rebuild-message-broker \
        ps-bet-maker ps-line-provider ps-message-broker \
        clean-bet-maker clean-line-provider clean-message-broker

# Start all services
all: up-message-broker sleep-before-up up-bet-maker up-line-provider
up: all

# Sleep 5 second
sleep-before-up:
	@echo "Waiting 5 seconds for Message Broker to initialize..."
	@$(SLEEP)

# Stop all services
down: down-bet-maker down-line-provider down-message-broker

# Rebuild all services
rebuild: rebuild-bet-maker rebuild-line-provider rebuild-message-broker

# Show status of all containers
ps: ps-bet-maker ps-line-provider ps-message-broker

# Clean all services
clean: clean-bet-maker clean-line-provider clean-message-broker

# Bet Maker commands
up-bet-maker:
	@echo "Starting Bet Maker..."
	@cd $(BET_MAKER_DIR) && $(DC_UP)

down-bet-maker:
	@echo "Stopping Bet Maker..."
	@cd $(BET_MAKER_DIR) && $(DC_DOWN)

rebuild-bet-maker:
	@echo "Rebuilding Bet Maker..."
	@cd $(BET_MAKER_DIR) && $(DC_REBUILD)

ps-bet-maker:
	@echo "Status for Bet Maker:"
	@cd $(BET_MAKER_DIR) && $(DC_PS)

clean-bet-maker:
	@echo "Cleaning Bet Maker..."
	@cd $(BET_MAKER_DIR) && $(DC_CLEAN)

# Line Provider commands
up-line-provider:
	@echo "Starting Line Provider..."
	@cd $(LINE_PROVIDER_DIR) && $(DC_UP)

down-line-provider:
	@echo "Stopping Line Provider..."
	@cd $(LINE_PROVIDER_DIR) && $(DC_DOWN)

rebuild-line-provider:
	@echo "Rebuilding Line Provider..."
	@cd $(LINE_PROVIDER_DIR) && $(DC_REBUILD)

ps-line-provider:
	@echo "Status for Line Provider:"
	@cd $(LINE_PROVIDER_DIR) && $(DC_PS)

clean-line-provider:
	@echo "Cleaning Line Provider..."
	@cd $(LINE_PROVIDER_DIR) && $(DC_CLEAN)

# Message Broker commands
up-message-broker:
	@echo "Starting Message Broker..."
	@cd $(MESSAGE_BROKER_DIR) && $(DC_UP)

down-message-broker:
	@echo "Stopping Message Broker..."
	@cd $(MESSAGE_BROKER_DIR) && $(DC_DOWN)

rebuild-message-broker:
	@echo "Rebuilding Message Broker..."
	@cd $(MESSAGE_BROKER_DIR) && $(DC_REBUILD)

ps-message-broker:
	@echo "Status for Message Broker:"
	@cd $(MESSAGE_BROKER_DIR) && $(DC_PS)

clean-message-broker:
	@echo "Cleaning Message Broker..."
	@cd $(MESSAGE_BROKER_DIR) && $(DC_CLEAN)