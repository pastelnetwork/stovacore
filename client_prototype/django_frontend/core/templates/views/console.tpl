{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mt-3">
        <h1>Pastel console</h1>
        <form method="post">
            <input type="hidden" name="csrfmiddlewaretoken" value="{{ csrf_token }}" />
            <table class="table">
                {{ form }}
            </table>
            <button type="submit" class="btn btn-success btn-center">Send</button>
        </form>
    </div>
</div>

<div class="row">
    <div class="col-sm-12 mt-3">
        <h5>Output:</h5>
        <pre>{{ output|pprint }}</pre>
    </div>
</div>
{% endblock %}
