# Pooling

This is a Django application to be deployed in any Django project.

It traces the pooling of samples from up to four 4x6 racks into pools on a fith 4x6 rack.

--------------
# Installation

- Add 'pooling' to the project installed apps in settings.
- Add the default number of samples per pool in settings as POOL_TUBE_SAMPLES (integer)
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
# Acknowledgments

- All errors in the code are mine: Victoriano Giralt

Good ideas come from Dr. mercedes Pérez input.

Bug crashing, testing and support come from the rest of the CWarriors core develpment team:

- Aitor Gastaminza
- Alex Gasulla
- Ramón Martínez

The protocol has been executed with the help on the field of:

- Mario Moncada
- Andrés Montes

Finally, all this project would not have been possible without the ideas and support of:

- Dr Rocio Martínez
- Dr. Andreu Veà

