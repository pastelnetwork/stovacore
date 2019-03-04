{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mt-3">
        <h3>Your task queue:</h3>
        {% for task in tasks %}
            identifier: {{ task["identifier"] }}
            done: {{ task["done"] }}
            exception: {{ task["exception"] }}<br />
        {% endfor %}
    </div>
</div>
{% endblock %}
