Improved the handling of invalid metric groups in the 'fetch_properties'
parameter in the metric definition file: So far, they were just silently
ignored. Now, a warning message is now shown on stdout and in the log
(and they continue to be ignored).
