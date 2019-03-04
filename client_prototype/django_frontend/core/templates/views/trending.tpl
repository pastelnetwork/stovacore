{% extends "views/base.tpl" %}

{% import "macros.tpl" as macros %}


{% block body %}
<div class="row">
    <div class="col-sm-12 mt-3">
        <h1>Trending: {{ resp }}</h1>
    </div>
</div>
{% endblock %}
