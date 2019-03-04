{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mt-3">
        <h1>Welcome to Pastel</h1>
        <h3>basedir: {{ pastel_basedir }}</h3>
    </div>
    {% for name, info in infos.items() %}
        <div class="col-sm-3 mt-3">
            <h5>{{ name }} info:</h5>
            <pre>{{ info|pprint }}</pre>
        </div>
    {% endfor %}
</div>
{% endblock %}
