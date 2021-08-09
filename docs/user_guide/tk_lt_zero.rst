iSnobal error: ``tk < 0``
=========================

One of the most common errors when running iSnobal is the
``tk < 0`` error. While this error is not very informative, the solution
is quite straightforward.

Why the error?
--------------

The error is occurring because the surface layer's temperature is below 0 degrees
Kelvin. This can happen when the surface energy budget for the timestep is negative
and the snowpack is loosing a large amount of energy (negative energy balance).
The negative energy balance can create a very cold snowpack and drive the temperature
to absolute zero.

This error typically occurs during cold and very windy conditions over a shallow snowpack, 
making the turbulent transfer the largest component of the energy balance.

How to fix
----------

Step 1
~~~~~~

The best method to fix this error is to increase the iSnobal mass thresholds to refine
and stabilize the turbulent transfer calculations. This can be achieved by using the
``thresh_small``, ``thresh_medium`` or ``thresh_normal`` in the ``[ipysnobal]`` section.

 .. note::

    We recommend to start changing the ``thresh_medium`` to start becasue this will target
    the shallow snowpack pixels.

    The default value is ``thresh_medium: 10`` and a good start is to change to
    ``thresh_medium: 20``.

.. code::

    [ipysnobal]
    thresh_normal:  60
    thresh_medium:  20   <---
    thresh_small:    1

Step 2
~~~~~~

After changing the configuration file, the model will need to be reran. Start the model
a day or few hours before the time step that crashed. Run for a few timesteps or until
the cold and windy condition is complete.

.. code::

    awsm config.ini

Step 3
~~~~~~

After the model is through the period, change the thresholds back and continue running.

.. code::

    [ipysnobal]
    thresh_normal:  60
    thresh_medium:  10   <---
    thresh_small:    1