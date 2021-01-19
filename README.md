# airflow-worker-logs-plugin
Airflow view plugin to fetch logs from worker instead of remote source like AWS / GCS

This is a work around for Airflow issue https://github.com/apache/airflow/issues/9610.

Add the code inside the template folder of your Airflow to add the view plugin. 

The plugin adds an extra button in the popup in the Tree view page, clicking on which it will open page with logs from worker instead of remote source.

<img src="https://github.com/raj-manvar/airflow-worker-logs-plugin/blob/main/extra_button_picture.png" width="600" height="600" />
