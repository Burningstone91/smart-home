"""Define persons in household."""

PERSONS = {
    "Dimitri": {
        "phone_gps": "device_tracker.dimitri_phone_gps",
        "phone_call_bool": "input_boolean.ongoing_call_dimitri",
        "phone_battery": "sensor.dimitri_phone_battery",
        "phone_charging": "binary_sensor.dimitri_phone_charging",
        "keys": "sensor.dimitri",
        "keys_topic": "location/dimitri_keys",
        "presence_state": "input_select.dimitri_presence",
        "notifier": "notify.dimitri_handy",
    },
    "Sabrina": {
        "keys": "sensor.sabrina",
        "keys_topic": "location/sabrina_keys",
        "presence_state": "input_select.sabrina_presence",
    },
}