  #!/bin/bash

  sudo systemctl restart distributor.service
  sudo systemctl status distributor.service

  sudo systemctl restart awstransfer.service
  sudo systemctl status awstransfer.service

  sudo systemctl restart statuslistener.service
  sudo systemctl status awstransfer.service