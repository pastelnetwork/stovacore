{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mt-3">
        <pre>{{ chaininfo|pprint }}</pre>
    </div>
</div>
{% endblock %}
