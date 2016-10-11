import flask
import json
import logging
import time;

LOG = logging.getLogger('api')
CONTROLLER = None
app = flask.Flask('concord232')
LOG.info("API Code Loaded")

def show_zone(zone):
    return {
        'partition': zone['partition_number'],
        'area': zone['area_number'],
        'group': zone['group_number'],
        'number': zone['zone_number'],
        'name': zone['zone_text'],
        'state': zone['zone_state'],
        'type': zone['zone_type'],
        #'bypassed': zone.bypassed,
        #'condition_flags': zone.condition_flags,
        #'type_flags': zone.type_flags,
    }


def show_partition(partition):
    return {
        'number': partition['partition_number'],
        'area': partition['area_number'],
        'arming_level': partition['arming_level'],
        'arming_level_code': partition['arming_level_code'],
        'partition_text': partition['partition_text'],
        'zones': sum(z['partition_number'] == partition['partition_number'] for z in CONTROLLER.zones.values()),


    }

@app.route('/panel')
def index_panel():
    try:
        result = json.dumps({
            'panel': CONTROLLER.panel
            })
        return flask.Response(result,
                              mimetype='application/json')
    except Exception as e:
        LOG.exception('Failed to index zones')

@app.route('/zones')
def index_zones():
    try:
        if not bool(CONTROLLER.zones):
            CONTROLLER.request_zones();
            
        while not bool(CONTROLLER.zones):
            time.sleep(0.25)

        result = json.dumps({
            'zones': [show_zone(zone) for zone in CONTROLLER.zones.values()]})
        return flask.Response(result,
                              mimetype='application/json')
    except Exception as e:
        LOG.exception('Failed to index zones')




@app.route('/partitions')
def index_partitions():
    try:
        if not bool(CONTROLLER.partitions):
            CONTROLLER.request_partitions();
         
        while not bool(CONTROLLER.partitions):
            time.sleep(0.25)

        result = json.dumps({
            'partitions': [show_partition(partition)
                           for partition in CONTROLLER.partitions.values()]})
        return flask.Response(result,
                              mimetype='application/json')
    except Exception as e:
        LOG.exception('Failed to index partitions')


@app.route('/command')
def command():
    args = flask.request.args
    if args.get('cmd') == 'arm':
        if args.get('type') == 'stay':
            CONTROLLER.arm_stay()
        elif args.get('type') == 'exit':
            CONTROLLER.arm_exit()
        else:
            CONTROLLER.arm_auto()
    elif args.get('cmd') == 'disarm':
        CONTROLLER.disarm(args.get('master_pin'))
    elif args.get('cmd') == 'keys':
        CONTROLLER.send_keys(args.get('keys'),args.get('group'))
    return flask.Response()

@app.route('/version')
def get_version():
    return flask.Response(json.dumps({'version': '1.1'}),
                          mimetype='application/json')

@app.route('/equipment')
def get_equipment():
    CONTROLLER.request_all_equipment()
    return flask.Response()    


@app.route('/all_data')
def get_all_data():
    CONTROLLER.request_dynamic_data_refresh()
    return flask.Response()    