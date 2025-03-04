<div class="panel" ng-controller="OrderView as showCase">
  <div class="panel-header">
    <button type="button" class="btn btn-primary pull-right" ng-click="showCase.excel()">Download Excel</button>
    <select class="hide form-control pull-right mr10" style="width: 155px;" ng-model="showCase.g_data.view" ng-change="showCase.change_datatable()">
      <option ng-repeat="view in showCase.g_data.views" value="{{view}}" ng-selected="view == showCase.g_data.view"> {{view}}</option>
    </select>
  </div>
  <div ng-include="'views/common/datatable.html'"></div>
  <div class="panel-footer">
    <button type="submit" class="btn btn-primary pull-right" ng-disabled="showCase.bt_disable" ng-click="showCase.generate_picklist()">Generate Picklist</button>
  </div>
</div>
