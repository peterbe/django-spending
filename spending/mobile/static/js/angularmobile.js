var module = angular.module('myApp', []);

module.config(function ($httpProvider) {
  $httpProvider.defaults.transformRequest = function(data){
    if (data === undefined) {
      return data;
    }
    return $.param(data);
  };
  $httpProvider.defaults.headers.post['Content-Type'] = ''
    + 'application/x-www-form-urlencoded; charset=UTF-8';
});

//
//var app = angular.module('AngularJSApp', []);

/*
angular.module('project', []).config(function($routeProvider) {
  $routeProvider.
    when('/mobile/auth/', {controller:SignInCtrl});//.
    //otherwise({redirectTo:'/'});
});
*/


function SpendingCtrl($scope, $http, $timeout) {
  // controlling which panels to show
  $scope.panels = {};
  $scope.panels.signin = true;
  $scope.panels.form = false;

  // controlling which inputs to show
  $scope.inputs = {};
  $scope.inputs.other_category = false;

  $scope.validationerrors = {};

  // other visibility items
  $scope.is_offline = true;  // assume the worst
  $scope.is_logged_in = false;
  $scope.success_message = null;

  $scope._csrf_token = null;

  $http.get('/mobile/auth/', { })
    .success(function(data, status) {
      $scope.is_offline = false;

      $scope._csrf_token = data.csrf_token;
      if (data.username) {
        $scope.username = data.username;
        $scope.panels.signin = false;
        $scope.panels.form = true;
      } else {
        throw "notimplemented";
      }
    })
    .error(function(data, status) {
      console.log('ERROR', data, status);
      $scope.data = data || "Request failed";
      $scope.status = status;
    });

  $scope.id_username = '';
  $scope.id_password = '';

  $scope.signin = function() {
    var data = {csrfmiddlewaretoken: $scope._csrf_token};
    if (!$scope.id_username) alert("Username not filled in");
    // https://github.com/angular/angular.js/issues/1460
    if (!$scope.id_password) alert("Password not filled in");
    data.username = $scope.id_username;
    data.password = $scope.id_password;
    //console.log(data);
    $http.post('/mobile/auth/', data)
      .success(function(data, status) {
        //console.log(data, status);
        if (data.username) {
          $scope.username = data.username;
          $scope.panels.signin = false;
          $scope.panels.form = true;
          $scope.is_logged_in = true;
          $scope.is_offline = false;
        } else {
          throw "notimplemented";
        }
      })
      .error(function(data, status) {
        console.log('ERROR', data, status);
        $scope.data = data || "Request failed";
        $scope.status = status;
      });
    };

  function any(sequence) {
    var something = false;
    angular.forEach(sequence, function(each) {
      if (each) something = true;
    });
    return something;

  }

  // submit an expense
  $scope.submit = function() {
    var category = $scope.category || null;
    if (category == 0) {
      // other_category must be set
      category = $scope.other_category;
      $scope.validationerrors.other_category = !category;
      $scope.validationerrors.category = false;
    } else {
      $scope.validationerrors.category = !category;
    }
    var amount = $scope.amount || null;
    $scope.validationerrors.amount = !amount;
    var date = $scope.date;
    var notes = $scope.notes;
    if (!any($scope.validationerrors)) {
      var data = {
         amount: amount,
         date: date,
        notes: notes,
        category: category,
        csrfmiddlewaretoken: $scope._csrf_token
      };
      $http.post('/mobile/submit/', data)
        .success(function(data, status) {
          if (data.errors) {
            angular.forEach(data.errors, function(key, message) {
              alert('ERROR ' + key + ': ' + message);
            });
          } else {
            $scope.success_message = data.success_message;
            $timeout(function() {
              $scope.success_message = null;
            }, 10 * 1000);
            $scope.inputs.other_category = false;
            document.getElementById('till').play();
          }

        })
        .error(function(data, status) {
          console.log('ERROR', data, status);
          $scope.data = data || "Request failed";
          $scope.status = status;
        });
    } else {
      console.log("VALIDATION TROUBLES", $scope.validationerrors);
    }
  };

  $scope.category = '';

  $scope.$watch('category', function(id) {
    if (id) {
      if (id == 0) {
        $scope.inputs.other_category = true;
        setTimeout(function() {
          $('input[name="other_category"]').focus();
        }, 100);
      } else {
        $scope.inputs.other_category = false;
      }
    }
  });

  $scope.categories = [];
  if (localStorage.getItem('spendingcategories')) {
    var spendingcategories = localStorage.getItem('spendingcategories');
    $scope.categories = JSON.parse(spendingcategories);
    $scope.categories.push({name: 'Other... (specify)', id: 0});
  } else {
    $http.get('/mobile/categories/', { })
      .success(function(data) {
        var _new_categories = [];
        angular.forEach(data.categories, function(each) {
          _new_categories.push({name: each[0], id: each[1]});
        });
        localStorage.setItem('spendingcategories', JSON.stringify(_new_categories));
        _new_categories.push({name: 'Other... (specify)', id: 0})
        $scope.categories = _new_categories;
      })
      .error(function(data, status) {
        console.log('ERROR', data, status);
      });
  }

};
