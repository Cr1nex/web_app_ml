# webml dev/deploy convenience targets.
#
# Examples:
#   make images                # build all four docker images
#   make kind-up               # create cluster + apply manifests + port-forward gateway
#   make kind-reload           # rebuild images, load into kind, restart deployments
#   make kind-down             # destroy the cluster
#
# Override the project / cluster / tag without editing the file:
#   make images TAG=v0.2
#   make kind-up CLUSTER=other

PROJECT ?= webml
CLUSTER ?= $(PROJECT)
TAG     ?= latest
NS      ?= $(PROJECT)

IMAGES := backend frontend mlflow ml-service

# Each image's build context + Dockerfile differ; this map captures both.
backend_CTX      := backend
frontend_CTX     := frontend
mlflow_CTX       := ml_service
ml-service_CTX   := ml_service
backend_DOCKER   := backend/Dockerfile
frontend_DOCKER  := frontend/Dockerfile
mlflow_DOCKER    := ml_service/src/deployment/Dockerfile
ml-service_DOCKER := ml_service/Dockerfile

REFS := $(foreach i,$(IMAGES),$(PROJECT)/$(i):$(TAG))

.PHONY: help tools check-tools images load kind-create kind-up kind-reload kind-down apply rollout fwd deploy-model \
        $(addprefix image-,$(IMAGES))

# Verify kind + kubectl are on PATH. `command -v` is POSIX, no shell deps.
# Fails fast with the install hint instead of letting `kind: command not found`
# escape from deep inside a target.
check-tools:
	@command -v docker  >/dev/null || { echo "docker not found.  Install Docker first."; exit 1; }
	@command -v kind    >/dev/null || { echo "kind not found.    Run: bash scripts/setup.sh"; exit 1; }
	@command -v kubectl >/dev/null || { echo "kubectl not found. Run: bash scripts/setup.sh"; exit 1; }

# Install kubectl + kind via the project's setup script (uses sudo).
tools:
	bash scripts/setup.sh

help:
	@echo "webml Makefile targets:"
	@echo "  tools           install kubectl + kind via scripts/setup.sh (uses sudo)"
	@echo "  images          build all four docker images"
	@echo "  image-<name>    build one image (backend, frontend, mlflow, ml-service)"
	@echo "  load            kind load all images into cluster '$(CLUSTER)'"
	@echo "  apply           kubectl apply -k k8s/"
	@echo "  rollout         wait for every deployment to be Available"
	@echo "  kind-create     create a fresh kind cluster '$(CLUSTER)'"
	@echo "  kind-up         create + build + load + apply + rollout"
	@echo "  kind-reload     rebuild images + load + restart deployments"
	@echo "  kind-down       delete cluster '$(CLUSTER)'"
	@echo "  fwd             port-forward gateway → localhost:8080"
	@echo "  deploy-model    train + promote + hot-reload ml-service pods"
	@echo ""
	@echo "Variables: PROJECT=$(PROJECT) CLUSTER=$(CLUSTER) TAG=$(TAG)"

# One target per image — depends on its Dockerfile + the whole context dir.
define image-rule
image-$(1):
	docker build -t $(PROJECT)/$(1):$(TAG) -f $$($(1)_DOCKER) $$($(1)_CTX)
endef
$(foreach i,$(IMAGES),$(eval $(call image-rule,$(i))))

images: $(addprefix image-,$(IMAGES))

load: check-tools images
	kind load docker-image --name $(CLUSTER) $(REFS)

kind-create: check-tools
	kind get clusters | grep -qx $(CLUSTER) || kind create cluster --name $(CLUSTER) --config k8s/kind-config.yaml

apply: check-tools
	kubectl apply -k k8s/

rollout:
	@for d in postgres redis rabbitmq mlflow backend ml-service frontend nginx-gateway; do \
	    echo "==> waiting for deployment/$$d"; \
	    kubectl -n $(NS) rollout status deployment/$$d --timeout=180s; \
	done

kind-up: kind-create load apply rollout
	@echo ""
	@echo "Cluster '$(CLUSTER)' is up. Open another shell and run:  make fwd"

# Rebuild + reload + bounce pods so they pick up the new image SHA. Useful
# during inner-loop development without a full kind-down/kind-up.
kind-reload: load
	@for d in backend frontend mlflow ml-service; do \
	    kubectl -n $(NS) rollout restart deployment/$$d; \
	done
	$(MAKE) rollout

kind-down: check-tools
	kind delete cluster --name $(CLUSTER)

fwd:
	kubectl -n $(NS) port-forward svc/nginx-gateway 8080:80

# Forwards $(NS) through so the script targets the right namespace if it
# was overridden. Pass extra args via ARGS="...", e.g.:
#   make deploy-model ARGS="--skip-train --restart"
deploy-model:
	python scripts/train_and_deploy.py --namespace $(NS) $(ARGS)
