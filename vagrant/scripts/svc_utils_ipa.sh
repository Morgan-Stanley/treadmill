function add_svc {
    echo Adding service: $1
    cp -v /home/vagrant/treadmill/vagrant/systemd/${1}_ipa.service \
       /etc/systemd/system/${1}.service

    /bin/systemctl daemon-reload
    /bin/systemctl enable $1.service --now
}

function del_svc {
    echo Deleting service: $1
    /bin/systemctl disable $1.service --now || /bin/true
    rm -vrf /etc/systemd/system/$1.service
    /bin/systemctl daemon-reload
}
