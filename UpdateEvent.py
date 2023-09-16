class UpdateEvent:
    def __init__(self, device_id, device_name, data):
        self.device_id = device_id
        self.device_name = device_name
        self.data = data
