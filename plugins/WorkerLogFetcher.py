import os
import urllib.parse

import airflow
import pendulum
from airflow import models
from airflow.configuration import conf
from airflow.models.baseoperator import BaseOperatorLink
from airflow.plugins_manager import AirflowPlugin
from airflow.settings import STORE_SERIALIZED_DAGS
from airflow.utils.db import provide_session
from airflow.utils.log.file_task_handler import FileTaskHandler
from airflow.www import utils as wwwutils
from airflow.www.forms import DateTimeForm
from flask import Blueprint, request
from flask_appbuilder import expose, BaseView as AppBuilderBaseView

airflow.load_login()
login_required = airflow.login.login_required

# Creating a flask appbuilder BaseView
class WorkerLogsBaseView(AppBuilderBaseView):

    default_view = "render"

    @expose("/")
    @login_required
    @wwwutils.action_logging
    @provide_session
    def render(self, session=None):
        dag_id = request.args.get("dag_id")
        task_id = request.args.get("task_id")
        execution_date = request.args.get("execution_date")

        if not dag_id or not task_id or not execution_date:
            return self.render_template(
                "airflow/circles.html", hostname="readact"  # Airflow 404 template
            )

        dttm = pendulum.parse(execution_date)
        form = DateTimeForm(data={"execution_date": dttm})
        dagbag = models.DagBag(
            os.devnull,  # to initialize an empty dag bag
            store_serialized_dags=STORE_SERIALIZED_DAGS,
        )
        dag = dagbag.get_dag(dag_id)
        ti = (
            session.query(models.TaskInstance)
            .filter(
                models.TaskInstance.dag_id == dag_id,
                models.TaskInstance.task_id == task_id,
                models.TaskInstance.execution_date == dttm,
            )
            .first()
        )
        ti.task = dag.get_task(ti.task_id)

        file_task_handler = FileTaskHandler(
            base_log_folder=conf.get("core", "BASE_LOG_FOLDER"),
            filename_template=conf.get("core", "LOG_FILENAME_TEMPLATE"),
        )
        logs, metadatas = file_task_handler.read(ti, None, None)
        return self.render_template(
            "worker_logs_plugin/template.html",
            logs=logs,
            dag=dag,
            title="Logs from worker",
            dag_id=dag.dag_id,
            task_id=task_id,
            execution_date=execution_date,
            form=form,
            root="",
            wrapped=conf.getboolean("webserver", "default_wrap"),
        )


v_appbuilder_view = WorkerLogsBaseView()
v_appbuilder_package = {
    "name": "Worker Logs",
    "category": "Browse",
    "view": v_appbuilder_view,
}

# Creating a flask blueprint to integrate the templates and static folder
bp = Blueprint(
    "worker_logs_plugin",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static/template",
)

# An extra button link in task page that redirect to logs from worker
class WorkerLogsLink(BaseOperatorLink):
    name = "Worker Logs"

    def get_link(self, operator, dttm):
        return (
            f'{os.getenv("AIRFLOW__WEBSERVER__BASE_URL")}'
            f"/workerlogsbaseview"
            f"?task_id={operator.task_id}&dag_id={operator.dag_id}"
            f"&execution_date={urllib.parse.quote(str(dttm))},"
        )


# Defining the plugin class
class AirflowWorkerLogsPlugin(AirflowPlugin):
    name = "worker_logs_plugin"
    flask_blueprints = [bp]
    appbuilder_views = [v_appbuilder_package]
    global_operator_extra_links = [
        WorkerLogsLink(),
    ]
