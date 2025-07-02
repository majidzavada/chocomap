import pytest
import testinfra

def test_services(host):
    mysql = host.service("mysql")
    redis = host.service("redis-server")
    assert mysql.is_running
    assert redis.is_running

def test_systemd_units(host):
    nginx = host.service("nginx")
    chocomap = host.service("chocomap")
    assert nginx.is_running
    assert chocomap.is_running

def test_ports(host):
    assert host.socket("tcp://0.0.0.0:80").is_listening
    assert host.socket("tcp://0.0.0.0:8000").is_listening

def test_files_and_directories(host):
    app_dir = host.file("/home/apps/chocomap")
    virtualenv = host.file("/home/apps/chocomap/venv")
    config_file = host.file("/home/apps/chocomap/ansible/group_vars/web.yml")

    assert app_dir.exists
    assert app_dir.user == "chocomap"
    assert virtualenv.exists
    assert virtualenv.user == "chocomap"
    assert config_file.exists
    assert config_file.user == "chocomap"
