<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="utf-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1">

    <title>Pastel wallet</title>

    <!-- Bootstrap core CSS-->
    <link href="/static/design/vendor/bootstrap/css/bootstrap.min.css" rel="stylesheet">

    <!-- Custom fonts for this template-->
    <link href="/static/design/vendor/fontawesome-free/css/all.min.css" rel="stylesheet" type="text/css">

    <!-- Page level plugin CSS-->
    <!--<link href="/static/design/vendor/datatables/dataTables.bootstrap4.css" rel="stylesheet">-->

    <!-- Custom styles for this template-->
    <link href="/static/design/css/sb-admin.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/design/css/index.css">
    <!--{# Favicon #}-->
    <!--<link rel="shortcut icon" href="/static/images/favicon.ico" />-->
    <!--<link rel="icon" href="/static/images/favicon.ico" />-->

    {% block extrahead %}
    {% endblock %}
</head>

<body id="page-top">
    {% block header %}
    <nav class="navbar navbar-expand navbar-dark bg-dark static-top">

      <a class="navbar-brand mr-1" href="/">Pastel</a>

      <button class="btn btn-link btn-sm text-white order-1 order-sm-0" id="sidebarToggle" href="#">
        <i class="fas fa-bars"></i>
      </button>

      <!-- Navbar Search -->
      <form class="d-none d-md-inline-block form-inline ml-auto mr-0 mr-md-3 my-2 my-md-0">
        <div class="input-group">
          <input type="text" class="form-control" placeholder="Search for..." aria-label="Search" aria-describedby="basic-addon2">
          <div class="input-group-append">
            <button class="btn btn-primary" type="button">
              <i class="fas fa-search"></i>
            </button>
          </div>
        </div>
      </form>

      <!-- Navbar -->
      <ul class="navbar-nav ml-auto ml-md-0">
        <li class="nav-item dropdown no-arrow mx-1">
          <a class="nav-link dropdown-toggle" href="#" id="alertsDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            <i class="fas fa-bell fa-fw"></i>
            <span class="badge badge-danger">9+</span>
          </a>
          <div class="dropdown-menu dropdown-menu-right" aria-labelledby="alertsDropdown">
            <a class="dropdown-item" href="#">Action</a>
            <a class="dropdown-item" href="#">Another action</a>
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="#">Something else here</a>
          </div>
        </li>
        <li class="nav-item dropdown no-arrow mx-1">
          <a class="nav-link dropdown-toggle" href="#" id="messagesDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            <i class="fas fa-envelope fa-fw"></i>
            <span class="badge badge-danger">7</span>
          </a>
          <div class="dropdown-menu dropdown-menu-right" aria-labelledby="messagesDropdown">
            <a class="dropdown-item" href="#">Action</a>
            <a class="dropdown-item" href="#">Another action</a>
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="#">Something else here</a>
          </div>
        </li>
        <li class="nav-item dropdown no-arrow">
          <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            <i class="fas fa-user-circle fa-fw"></i>
          </a>
          <div class="dropdown-menu dropdown-menu-right" aria-labelledby="userDropdown">
            <a class="dropdown-item" href="#">Settings</a>
            <a class="dropdown-item" href="#">Activity Log</a>
            <div class="dropdown-divider"></div>
            <a class="dropdown-item" href="#" data-toggle="modal" data-target="#logoutModal">Logout</a>
          </div>
        </li>
      </ul>
    </nav>
    {% endblock %}

    <div id="wrapper">

        <!-- Sidebar -->
        <ul class="sidebar navbar-nav">
        <li class="nav-item active">
          <a class="nav-link" href="/">
            <i class="fas fa-fw fa-tachometer-alt"></i>
            <span>Dashboard</span>
          </a>
        </li>
          <!--<li class="nav-item dropdown">-->
          <!--<a class="nav-link dropdown-toggle" href="#" id="pagesDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">-->
            <!--<i class="fas fa-fw fa-folder"></i>-->
            <!--<span>Pages</span>-->
          <!--</a>-->
          <!--<div class="dropdown-menu" aria-labelledby="pagesDropdown">-->
            <!--<h6 class="dropdown-header">Login Screens:</h6>-->
            <!--<a class="dropdown-item" href="login.html">Login</a>-->
            <!--<a class="dropdown-item" href="register.html">Register</a>-->
            <!--<a class="dropdown-item" href="forgot-password.html">Forgot Password</a>-->
            <!--<div class="dropdown-divider"></div>-->
            <!--<h6 class="dropdown-header">Other Pages:</h6>-->
            <!--<a class="dropdown-item" href="404.html">404 Page</a>-->
            <!--<a class="dropdown-item" href="blank.html">Blank Page</a>-->
          <!--</div>-->
        <!--</li>-->
        <li class="nav-item">
          <a class="nav-link" href="/tasks"><i class="fas fa-fw fa-database"></i>&nbsp;<span>Tasks</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/walletinfo"><i class="fas fa-fw fa-wallet"></i>&nbsp;<span>Wallet</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/identity"><i class="fas fa-fw fa-address-card"></i>&nbsp;<span>Identity</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/portfolio"><i class="fas fa-fw fa-briefcase"></i>&nbsp;<span>Portfolio</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/exchange"><i class="fas fa-fw fa-bars"></i>&nbsp;<span>Exchange</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/trending"><i class="fas fa-fw fa-chart-area"></i>&nbsp;<span>Trending</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/browse"><i class="fas fa-fw fa-table"></i>&nbsp;<span>Browse</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/register"><i class="fas fa-fw fa-plus"></i>&nbsp;<span>Register Art</span></a>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="/console"><i class="fas fa-fw fa-terminal"></i>&nbsp;<span>Console</span></a>
        </li>
        <li class="nav-item dropdown">
          <a class="nav-link dropdown-toggle" href="#" id="pagesDropdown" role="button" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
            <i class="fas fa-fw fa-folder"></i>
            <span>Block Explorer</span>
          </a>
            <div class="dropdown-menu" aria-labelledby="pagesDropdown">
                <h6 class="dropdown-header">Block Explorer</h6>
                <a class="dropdown-item" href="/explorer/chaininfo">Chaininfo</a>
                <a class="dropdown-item" href="/explorer/block">Blocks</a>
                <a class="dropdown-item" href="/explorer/transaction">Transactions</a>
                <a class="dropdown-item" href="/explorer/address">Addresses</a>
                <!--<div class="dropdown-divider"></div>-->
                <!--<h6 class="dropdown-header">Other Pages:</h6>-->
                <!--<a class="dropdown-item" href="404.html">404 Page</a>-->
                <!--<a class="dropdown-item" href="blank.html">Blank Page</a>-->
              </div>
        </li>
      </ul>

        <div id="content-wrapper">

        <div class="container-fluid">
            {% block body %}
            {% endblock %}
        </div>
    </div>

    {% block footer %}
        <footer class="sticky-footer">
          <div class="container my-auto">
            <div class="copyright text-center my-auto">
              <span>Copyright © Pastel 2018</span>
            </div>
          </div>
        </footer>
    {% endblock %}

    {% block scripts %}
        <!-- Bootstrap core JavaScript-->
        <script src="/static/design/vendor/jquery/jquery.min.js"></script>
        <script src="/static/design/vendor/bootstrap/js/bootstrap.bundle.min.js"></script>
    {% endblock %}
</body>

</html>
