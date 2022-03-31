# Destroy HTTP trigger
cd http/ && pulumi destroy -f -y

cd ..

# Destroy storage trigger
cd storage/ && pulumi destroy -f -y

cd ..

# Destroy queue trigger
cd queue/ && pulumi destroy -f -y

cd ..

# Destroy infrastructure
cd infra/ && pulumi destroy -f -y

cd ..

# Destroy shared resources (must be done last due to how pulumi tracks resources)
cd shared/ && pulumi destroy -f -y