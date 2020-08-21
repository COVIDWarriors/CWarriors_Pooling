# Pooling

This is a Django application to be deployed in any Django project.

It traces the pooling of samples from up to four 4x6 racks into pools on a fith 4x6 rack.

--------------
# Moral pre-requisite

I've invested a sizeable amount of my free time, even denting into my hours of sleep, in order to contribute to the fight against the global pandemic. If you use this code for controling protocols running on Opentrons robots you MUST (RFC 2119) publish your protocols for the global good. I have no way to force anyone to do this except through this paragraph, thus, the moral pre-requisite. Thank you.

--------------
# Installation

- Add 'pooling' to the project installed apps in settings.
- Add the default number of samples per pool in settings as POOL_TUBE_SAMPLES (integer)
- Add a refresh interval for displaying the robot page while wainting for updates form the real hardware in setings as POOLING_REFRESH in seconds.
- Add the application to the project urls.py with

   ```python
   url(r'^pooling/', include('pooling.urls')),
   ```

- Finally, _makemigrations_ and _migrate_

--------------
# Usage

1. Create robots and technicians using the admin interface.
2. Go to your project "pooling" URL with a browser.
3. Using the leftmost button on the "controls" pannel on top, load a sample batch from a CSV file, that MUST (RFC 2119) have a column named "code" that contains the sample codes. All other columns are ignored.
4. Add samples by entering their code in the "Load samples ..." panel in the middle.
5. Add tubes by entering their code in the "Load pool tubes ..." panel in the middle.
6. Move the samples. There are two options:
  - If the robot has no connection to the server, once the process is finished, press "End pooling" button in the middle panel.
  - If the robot has IP connection to the server, the protocol will report each sample move to the server, and they will be reflected on the page.
7. Once pooling has finished, press the red "Remove pools rack" button on the middle panel.
8. That's all folks.

--------------
# Code for sending moves from the robots

If you want to send teal moves from your robots to the tracing server, you have to add Python requests to your protocols and send lists of moves to the server. 

The movements on the list MUST (RFC2119) be dictionaries like:

   ```python
   {'source': {'tray': 1, 'row': 'A', 'col': 1}, 
   'destination': {'tray': 2, 'row': 'A', 'col': 1}}
   ```

Then, append each movement like above to a list and send to the server using requests.post, like

   ```python
   response=requests.post('http://serverip/path/pooling/movesample',json=data)
   ```

_serverip_ is your server IP address or name (Django has to be operational at that IP or name.
_path_ is the path where your Django project is installed
_data_ is the list of movement dictionaries (it may be just one movement)

--------------
# Acknowledgments

- All errors in the code are mine: Victoriano Giralt

Good ideas come from Dr. Mercedes Pérez input.

Bug crashing, testing and support come from the rest of the CWarriors core develpment team:

- Aitor Gastaminza
- Alex Gasulla
- Ramón Martínez

The protocol has been executed with the help on the field of:

- Mario Moncada
- Andrés Montes

Finally, all this project would not have been possible without the ideas and support of:

- Dr. Rocio Martínez
- Dr. Andreu Veà

