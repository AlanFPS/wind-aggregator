deploy:
	terraform -chdir=iac init
	terraform -chdir=iac apply -auto-approve
destroy:
	terraform -chdir=iac destroy -auto-approve