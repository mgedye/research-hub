# Copy this file to config.R and set db_path to the location of research.db.
# While working from the hub/ root .Rproj, here::here("research.db") works as-is.
# In a standalone project repo, use an absolute path, e.g.:
#   db_path <- "/home/username/Documents/research/hub/research.db"
db_path <- here::here("research.db")
