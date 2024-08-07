echo "Deploying latest version of AdventureLog"
docker compose pull
echo "Stating containers"
docker compose up -d
echo "All set!"