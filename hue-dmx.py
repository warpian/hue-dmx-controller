from DmxController import DmxController

if __name__ == "__main__":
    controller = DmxController()
    controller.send_heartbeat()
    controller.track_and_update_fixtures()

