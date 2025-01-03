# Eeprom
Electrically Erasable Programmable Read-Only Memory (eeprom) is non-volatile memory of the ENTTEC where some of its basic settings are stored. 
This readme contains instructions how to reprogram the Enttec eeprom if the serial number cannot be found.

# requirements
- eeprom utilities
```bash
sudo apt-get install libftdi1-2 libftdi1-dev libftdi1-dbg ftdi-eeprom
ftdi_eeprom --help
```

# usage
```bash
$ ftdi_eeprom --flash-eeprom ftdi_eeprom.conf
```