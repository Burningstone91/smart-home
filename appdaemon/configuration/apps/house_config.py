"""Define persons in household, house itself and house modes"""

PERSONS = {
    'Dimitri': {
        'phone': 'device_tracker.dimitri_phone',
        'phone_call_bool': 'input_boolean.ongoing_call_dimitri',
        'keys': 'sensor.dimitri',
        'presence_state': 'input_select.dimitri_presence',
        'notifier': 'notify.dimitri_handy'
    },
    'Sabrina': {
        'phone': 'device_tracker.sabrina_phone',
        'phone_call_bool': 'input_boolean.ongoing_call_sabrina',
        'keys': 'sensor.sabrina',
        'presence_state': 'input_select.sabrina_presence'
    }
}

HOUSE = {
    'alarm_state': 'input_select.alarm_state',
    'presence_state': 'input_select.house_presence',
    'last_motion': 'input_select.last_motion'
}

MODES = {
    'cleaning_mode': 'input_boolean.cleaning_mode',
    'guest_mode': 'input_boolean.guest_mode',
    'sleep_mode': 'input_boolean.sleep_mode',
    'dimitri_chill_mode': 'input_boolean.dimitri_chill_mode'
}
