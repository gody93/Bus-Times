# Bus-Times

Този код ви дава възможност да вземете оставащото време до пристигане на автобуси на дадена спирка. За да го подкарате в Home Assistant е нужно да сте конфигурирали аddon-a AppDaemon, който ви позволява да 
изпълнявате код написан на питон. При HAOS в config/ директорията създавам папка appdaemon/ и в нея apps/ . В apps/ добавям apps.yaml, който отговаря за изпълняването на кода и 
get_schedules.py
```
sofia_traffic_sensor:
  module: get_schedules <- името на .py файла
  class: SofiaTrafficSensor <- името на класа
  stop_id: "1287" <- кода на спирката взет от сайта на Sofia Traffic
  sensor_name: "sensor.bus_stop_info" <- сензора който искате да се ъпдейтва в HA
```
За повече от една спирка добавете ново entry в apps.yaml като смените stop_id и sensor_name с желаните от вас. За промяна на съдържанието което връща програмата бърникайте във функцията update_sensor
