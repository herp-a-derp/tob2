#!/bin/bash

set -e

# if [ "$(id -u)" != "0" ]; then
#    echo "This script must be run as root. Please enter your password for sudo." 1>&2
#    sudo -H env PATH=$PATH INTERNAL_SUDO=TRUE "$0" "$@"
#    exit 0;
# else
#   if [ $INTERNAL_SUDO != "TRUE" ]; then
#     echo "Please allow the script to 'sudo' internally, it has to be done a specific"
#     echo "way to properly preserve some environment variables."
#     exit 1
#   fi
# fi

echo "Fetching db dump from remote server";
sudo -H -u herp -- bash -c "ssh client@ks1 'sudo -u postgres pg_dump --clean -d tobdb | xz' | pv -cN Db-Fetch-Progress > ../dbBak/tob_db_dump_$(date +%Y-%m-%d).sql.xz";
sudo -H -u herp -- bash -c "ssh client@ks1 'tar -c /media/Storage/stories | xz' | pv -cN Story-Fetch-Progress > ../dbBak/tob_cover_dump_$(date +%Y-%m-%d).tar.xz";
# echo "Updating local database from dump file";
# sudo -H -u durr -- xz -d ../dbBak/tob_db_dump_$(date +%Y-%m-%d).sql.xz -c | pv -c | ssh tob user@10.1.1.61 -t "psql -d tobdb"
echo "Done!"
