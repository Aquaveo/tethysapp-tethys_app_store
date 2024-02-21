var $table = $("#mainAppsTable")



const keyLookup = {
  keywords: "Tags",
  description: "Description",
  license: "License",
  author_email: "App Developer Email",
  
}


function getResourceValue(key, index, apps) {

  var return_val;
  // return return_val
  if (apps) {
    if (apps[index]) {
      let app = apps[index]
      if (key in app) {
        return_val = app[key]
        return return_val
      }
      if (key in app["metadata"]) {
        return_val = app["metadata"][key]
        return return_val
      }

      else{

        var return_val = ""
        Object.keys(app["metadata"]).forEach(function(storeName){
          if(key in app["metadata"][storeName]){
            var val_attr = app["metadata"][storeName][key]
            if (val_attr){
              return_val += `${val_attr}`
            }
          }
        })
        return return_val
      }
    }
  }
}

function getResourceValueByName(key, name, apps) {
  if (apps) {
    let currentResource = apps.filter((resource) => resource.name == name)
    if (currentResource.length > 0) {
      let app = currentResource[0]
      if (key in app) {
        return app[key]
      }
      if (key in app["metadata"]) {
        return app["metadata"][key]
      }
      if(name in app["metadata"]){
        if(key in app["metadata"][name]){
          return app["metadata"][name][key]
        }
      }

      
    }
  }
}

function getHtmlElementIfExists(key, index, apps) {
  let val = getResourceValue(key, index, apps)
  if (val) {
    return `<li><strong>${keyLookup[key]}</strong>: ${val}</li>`
  }
}

function detailFormatter(index, row) {
  var html = ["<ul>"]
  Object.keys(keyLookup).forEach((key) =>
    html.push(getHtmlElementIfExists(key, index, availableApps))
  )
  html.push("</ul>")
  return html.join("")
}

function detailFormatterInstalledApps(index, row) {
  var html = ["<ul>"]
  Object.keys(keyLookup).forEach((key) =>
    html.push(getHtmlElementIfExists(key, index, installedApps))
  )
  html.push("</ul>")
  return html.join("")
}

function operateFormatter(value, row, index) {

  if (
    typeof value != 'object' &&
    !Array.isArray(value) &&
    value !== null
  ){
    return [
      '<a class="install button-spaced" href="javascript:void(0)" title="Install">',
      `<button type="button" class="btn btn-info btn-outline-secondary btn-xs">Install</button>`,
      "</a>",
      '<a class="github button-spaced" href="javascript:void(0)" title="Github">',
      `<button type="button" class="btn btn-primary btn-outline-secondary btn-xs">Github</button>`,
      "</a>"
    ].join("")
  }
  else{
    var object_row = value;
    var html = ''
    var index_label_color = 0
    for (const [key, value2] of Object.entries(object_row)) {
      html += `<div class="labels_container"> <p class="store_label btn btn-outline-${label_styles(index_label_color)} btn-xs"> #${key}</p>
        <p class="store_label_val">
          <a class="install button-spaced" href="javascript:void(0)" title="Install">
            <button type="button" class="btn btn-info btn-outline-secondary btn-xs">Install</button>
          </a>
          <a class="github_${key} button-spaced" href="${row['metadata'][key]['dev_url']}" target="_blank" title="Github">
            <button type="button" class="btn btn-primary btn-outline-secondary btn-xs">Github</button>
          </a>
        </p>
      </div>`
      index_label_color += 1;

    } 
    return html

  }

}

function operateFormatter2(value, row, index) {
  let buttons = [
    '<a class="uninstall button-spaced" href="javascript:void(0)" title="Uninstall">',
    `<button type="button" class="btn btn-info btn-warning btn-xs">Uninstall</button>`,
    "</a>"
    // '<a class="reconfigure button-spaced" href="javascript:void(0)" title="Configure">',
    // `<button type="button" class="btn btn-info btn-outline-secondary btn-xs">Configure</button>`,
    // "</a>"
  ]

  if (row.updateAvailable) {
    buttons.push(
      `<a class="update button-spaced" href="javascript:void(0)" title="Update"><button type="button" class="btn btn-primary btn-success btn-xs">Update</button></a>`
    )
  }

  return buttons.join("")
}

function mergedNameFormatter(value, row, index){
  var htmlStr = checkInstalledInAvailable(row,value)
  return htmlStr
  // return`<span class="custom-label">${value}</span></div>`
}
function installedRowStyle(row){
  if ('installedVersion' in row){
    return {
      classes: 'class-row-installed'
    }
  }
  else{

    return {
      classes: 'class-row-uninstalled'
    }
  }
}
function checkInstalledInAvailable(row,value){
  var htmlStr =`<span class="custom-label">${value}</span>`
  if ('installedVersion' in row){ //check it is not a row from installed apps.
    for(channel in row['installedVersion']){
      for(label in row['installedVersion'][channel]){
        htmlStr += `<span class="labels_container" style="display: inline-block;"> `
        htmlStr += `<span class="custom-label label-color-${labels_style_dict[channel]["channel_style"]} label-outline-xs"> <i class="bi bi-shop"></i> ${channel} </span>`
        htmlStr += `<span class="custom-label label-color-${labels_style_dict[channel]["label_styles"][label]} label-outline-xs"><i class="bi bi-tags"></i> ${label}</span>`
        htmlStr += `<span class="custom-label label-outline-xs label-color-gray">${row['installedVersion'][channel][label]}</span>`
        htmlStr += `</span>`
      }
    }

  }
  return htmlStr
}


function mergedTypeFormatter(value, row, index){
  if (value=="tethysapp") {
    return "Tethys App"
  } else if (value=="proxyapp") {
    return "Proxy App"
  } else {
    return "Unknown"
  }
}


function mergedFieldsFormatter(value, row, index){
  // console.log(incompatibleApps)

  var html_str = '<div>';
  var wasAdded = false;
  for(channel in value){
    // html_str += `<div class="multiple_stores_labels">`
    for (label in value[channel]){
      if (value[channel][label] !== null && value[channel][label] !== ""){
        if(!wasAdded){
          html_str += `<div class="channels_container"> <div><span class="store_label btn label-outline-${labels_style_dict[channel]["channel_style"]} label-outline-xs"> <i class="bi bi-shop"></i> ${channel} </span></div><span class="labels_container"> `;
        }
        html_str += `<div><span class="custom-label label-outline-${labels_style_dict[channel]["label_styles"][label]} label-outline-xs"><i class="bi bi-tags"></i> ${label}</span></div><div><span class="label-outline-xs label-color-gray">${value[channel][label]}</span></div>`
        wasAdded = true
      }
    }
    html_str += `</span></div>`
    wasAdded = false
  }
  return html_str
}

function addHtmlForUpdateApp(row){
  var html_str = ``
  if('updateAvailable' in row){
    for(channel in row['updateAvailable']){
      for(label in row['updateAvailable'][channel]){
        if(row['updateAvailable'][channel][label]){
          html_str +=`<a class="update button-spaced" href="javascript:void(0)" title="Update"><button type="button" id="${channel}_${label}_update" class="custom-label label-color-primary label-outline-xs">Update</button></a>`  
        }
      }
    }
  }
  return html_str
}

function ProxyAppActionFormatter(value, row, index) {
  let ProxyApp = row["name"]
  let deleteButton =  `<button type="button" id="${ProxyApp}_deleteProxy" style="margin-left:5px" class="custom-label label-color-danger label-outline-xs proxyAppDelete">Delete</button>`
  let updateButton =  `<button type="button" id="${ProxyApp}_updateProxy" style="margin-left:5px" class="custom-label label-color-warning label-outline-xs proxyAppUpdate">Update</button>`
  let submitButton =  `<button type="button" id="${ProxyApp}_submitProxy" style="margin-left:5px" class="custom-label label-color-primary label-outline-xs proxyAppUploadToStore">Submit to App Store</button>`
  return deleteButton + updateButton + submitButton
}

function mergedOperateFormatter(value, row, index){

  var html_str = `<div class="store_label_val">`
  html_str += getVersionsHTML_dropdown(row,row.hasOwnProperty('installedVersion'),false);
  for( channel in value){
    for (label in value[channel]){
      if(value[channel][label]){
        html_str += `<a class="uninstall button-spaced" href="javascript:void(0)" title="Uninstall">
        <button type="button" id="${channel}__${label}__uninstall" class="custom-label label-color-danger label-outline-xs"><i class="bi bi-dash-lg"></i> Uninstall</button>
        </a>`
        html_str +=`<a class="update button-spaced" href="javascript:void(0)" title="Update"><button type="button" id="${channel}_${label}_update" class="custom-label label-color-warning label-outline-xs"><i class="bi bi-stack"></i> Update </button></a>`  
      }
    }
  }
  html_str += `</div>`
  return html_str
}


// implement this and all the others
function mergedDetailFormatter(value, row, index){
  var object_for_table_body = {}
  var table_html = '<table class="table_small_font table table-light table-sm table-hover">';
  var table_header = '<thead class="table-dark"><tr><th scope="col">Last Version metadata</th>'
  var table_body = "<tbody>"
  for (key in row){
    if (key == 'license'){
      for (channel in row[key]){
        for (label in row[key][channel]){
          // table_header += `<th scope="col">${channel}-${label}</th>`
          table_header += `<th scope="col"><div style="display:flex;justify-content: center;">`;
          table_header +=  `<span class="store_label custom-label label-outline-${labels_style_dict[channel]["channel_style"]} label-outline-xs"><i class="bi bi-shop"></i>${channel}</span>`;
          table_header +=  `<span class="label_label custom-label label-outline-${labels_style_dict[channel]["label_styles"][label]} label-outline-xs"><i class="bi bi-tags"></i>${label}</span>`;
          table_header += `<div></th>`
          try{
            var normal_json = row[key][channel][label];
            var licenseChannnelLabel = JSON.parse(normal_json.replace(/'/g, '"'));
            // var wasAdded = false
            for (license_attr in licenseChannnelLabel){
              if(license_attr in object_for_table_body == false){
                object_for_table_body[license_attr] = []
                object_for_table_body[license_attr].push(licenseChannnelLabel[license_attr])
              }
              else{
                object_for_table_body[license_attr].push(licenseChannnelLabel[license_attr])
              }
            }
          }
          catch(e){
            console.log(e)
            continue
          }
        }

      }
      table_header +=`</tr></thead>`

    }
  }

  for(license_attr in object_for_table_body){
    table_body += `<tr><th>${license_attr}</th>`
    for(license_attr_index in object_for_table_body[license_attr]){
      if(license_attr == 'name' && object_for_table_body[license_attr][license_attr_index] == 'release_package' ){
        object_for_table_body[license_attr][license_attr_index] = row['name']
      }
      if (license_attr == 'dev_url' || license_attr == 'url'){
        var icon_logo = (license_attr == 'dev_url') ? 'github' : 'box-arrow-right';

        table_body += `<td><a class="github_type button-spaced" href="${object_for_table_body[license_attr][license_attr_index]}" target="_blank" title="Github">
          <button type="button" class="custom-label label-outline-xs label-color-gray"><i class="bi bi-${icon_logo}"></i></button>
        </a></td>`

      }
      else{
        table_body += `<td><span class="custom-label label-outline-xs label-color-gray">${object_for_table_body[license_attr][license_attr_index]}</span></td>`
      }
    }
    table_body += `</tr>`
  }
  table_body += `</tbody>`
  if(table_body !== "<tbody></tbody>"){
    table_html += `${table_header}${table_body}</table>`
  }
  else{
    table_html = `No Metadata Available`
  }

  return table_html
}

function fieldsFormatter(value, row, index){
  console.log(value)
  console.log(row)
  console.log(index)
  if (
    typeof value != 'object' &&
    !Array.isArray(value) &&
    value !== null
  ) {
    return value

  }
  else{
    if ("author" in value){
      return value.author
    }
    else{
      var html = '<div class="multiple_stores_labels">'
      var object_row = value
      // console.log(object_row)

      var index_label_color = 0
      for (const [key, value2] of Object.entries(object_row)) {
        if (
          typeof value2 != 'object' &&
          !Array.isArray(value2) &&
          value2 !== null
        ){
          html += `<div class="labels_container"> <span class="store_label btn btn-outline-${label_styles(index_label_color)} btn-xs"> #${key} </span> <span class="store_label_val">${value2}</span></div>`        
        }
        else{
          if(value2.author != ""){
            html += `<div class="labels_container"> <span class="store_label btn btn-outline-${label_styles(index_label_color)} btn-xs"> #${key} </span> <span class="store_label_val">${value2.author}</span></div>`
          }
          // else{
          //   html += `<div class="labels_container"> <span class="store_label btn-outline-secondary btn-xs"> #${key} </span > <span class="store_label_val"> No Data Provided</span></div>`
          // }
        }
        index_label_color += 1;
      }

      html += '</div>'
    }

  }
  return html

}

function writeTethysPlatformCompatibility(e, row) {
  let appList = $(e.target).attr("class").includes("incompatible-app") ? incompatibleApps : availableApps
  // Get the currently selected app
  let appName = getResourceValueByName("name", row.name, appList)
  // Get the currently selected version
  let selectedVersion = $("#versions option:selected").val()
  // Get the compatibility for that version
  let tethysCompatibility = updateTethysPlatformCompatibility(appName, selectedVersion, appList)
}
function writeTethysPlatformCompatibility_new(e, row,channel,label) {
  // Get the currently selected version
  // let selectedVersion = $("#versions option:selected").val().split("__")[2];
  let selectedVersion = $(e.target).attr("innerText");

  // Get the compatibility for that version
  let tethysCompatibility = updateTethysPlatformCompatibility_new(row, selectedVersion,channel,label)
}


function get_channel_label_from_id(e){
  let channel_label = $(e.target).attr("id").split('__')
  let channel = channel_label[0];
  let label = channel_label[1];
  return [channel,label]
}

function chooseVersion(app_name, app_type, channel, label, version, div_element){
  var htmlLatestVersion=''
  htmlLatestVersion += `<span class="labels_container" style="display: inline-block;"> `
  htmlLatestVersion += `<span class="custom-label label-color-${labels_style_dict[channel]["channel_style"]} label-outline-xs"> <i class="bi bi-shop"></i> ${channel} </span>`
  htmlLatestVersion += `<span class="custom-label label-color-${labels_style_dict[channel]["label_styles"][label]} label-outline-xs"><i class="bi bi-tags"></i> ${label}</span>`
  htmlLatestVersion += `<span class="custom-label label-outline-xs label-color-gray">${version}</span>`
  htmlLatestVersion += `</span>`

  $(`#${div_element}`).html(
    `Are you sure you would like to update the <strong>${
      app_name
    }</strong> app to version ${htmlLatestVersion}? `
  )

  if (app_type === "proxyapp") {
    app_name = "proxyapp_" + app_name
  }
  updateData = {
    name: app_name,
    app_type: app_type,
    channel: channel,
    label: label,
    version: version
  }
}


window.operateEvents = {
  "click .install": function(e, value, row, index) {
    
    $("#mainCancel").show()
    let n_div = $("#notification")
    let n_content = $("#notification .lead")
    let isUsingIncompatible = $(e.target).attr("class").includes("incompatible-app")
    let appList = isUsingIncompatible ? incompatibleApps : availableApps
    n_content.empty();
    n_div.modal({ backdrop: "static", keyboard: false })
    n_div.modal('show')
    $("#goToAppButton").hide()

    notifCount = 0
    // Setup Versions
    let appName = row['name'];
    $("#installingAppName").text(appName)
    installData["name"] = appName
    let channel_and_label = get_channel_label_from_id(e);
    let selectedVersion = e.target.innerText;
    let app_type = row['app_type'];
    if (app_type === "proxyapp") {
      appName = "proxyapp_" + appName
    }
    n_content.append(htmlHelpers.versions(appName, channel_and_label[0], channel_and_label[1], selectedVersion, isUsingIncompatible))
    writeTethysPlatformCompatibility_new(e, row, channel_and_label[0],channel_and_label[1])
  },

  "click .uninstall": function(e, value, row, index) {
    $("#uninstallingAppNotice").html(
      `Are you sure you would like to uninstall <strong>${
        row["name"]
      }</strong> app from your Tethys Portal? 
      \n This will remove all associated files and data stored in any linked persistent stores.`
    )
    let appType = row['app_type'];
    let appName = row["name"];
    if (appType === "proxyapp") {
      appName = "proxyapp_" + appName
    }
    uninstallData = {
      name: appName,
      app_type: appType
    }
    $("#uninstallingAppNotice").show()
    $("#doneUninstallButton").hide()

    $("#yesUninstall").show()
    $("#noUninstall").show()
    $("#uninstall_processing_label").empty()
    $("#uninstallNotices").empty()
    $("#uninstall-app-modal").modal({ backdrop: "static", keyboard: false })
    $("#uninstall-app-modal").modal("show")
  },

  "click .deleteProxyApp": function(e, value, row, index) {
    let ProxyApp = row["name"]
    console.log(ProxyApp)
  },

  "click .update": function(e, value, row, index) {
    let n_content = $("#update-notices .lead")
    // Find The installed App's version
    let installedApp = row["name"]
    for(channel in row['installedVersion']){
      for(label in row['installedVersion'][channel]){
        let htmlCurrentVersion = '';
        htmlCurrentVersion += `<span class="labels_container" style="display: inline-block;"> `
        htmlCurrentVersion += `<span class="custom-label label-color-${labels_style_dict[channel]["channel_style"]} label-outline-xs"> <i class="bi bi-shop"></i> ${channel} </span>`
        htmlCurrentVersion += `<span class="custom-label label-color-${labels_style_dict[channel]["label_styles"][label]} label-outline-xs"><i class="bi bi-tags"></i> ${label}</span>`
        htmlCurrentVersion += `<span class="custom-label label-outline-xs label-color-gray">${row['installedVersion'][channel][label]}</span>`
        htmlCurrentVersion += `</span>`

        let htmlLatestVersion = '<span>';
        htmlLatestVersion += `<span class="labels_container" style="display: inline-block;"> `
        htmlLatestVersion += `<span class="custom-label label-color-${labels_style_dict[channel]["channel_style"]} label-outline-xs"> <i class="bi bi-shop"></i> ${channel} </span>`
        htmlLatestVersion += `<span class="custom-label label-color-${labels_style_dict[channel]["label_styles"][label]} label-outline-xs"><i class="bi bi-tags"></i> ${label}</span>`
        htmlLatestVersion += `<span class="custom-label label-outline-xs label-color-gray">${row['latestVersion'][channel][label]}</span>`
        htmlLatestVersion += `</span>`
        htmlLatestVersion += `<button class="custom-label label-outline-xs label-outline-success pull-right" id="choose-version-update" onClick="chooseVersion('${row['name']}', '${row['app_type']}', '${channel}', '${label}', '${row['latestVersion'][channel][label]}', 'update-app-notice')" >Choose Version</button>`
        htmlLatestVersion += `</span>`
        $("#current-version-update").html(htmlCurrentVersion);
        $("#latest-version-update").html(htmlLatestVersion);
      }
    }

    var htmlNewInstall = `<div class="store_label_val">`
    htmlNewInstall += getVersionsHTML_dropdown(row,false,true);
    htmlNewInstall +=`</div>`
    $("#install-dropdown-update").html(htmlNewInstall);
    let dropdowns = document.querySelectorAll('.dropdown-toggle')
    dropdowns.forEach((dd)=>{
      
      dd.removeEventListener('click',eventClickDropdown)
      dd.addEventListener('click', eventClickDropdown)
    })
    let installDropdowns = document.querySelectorAll('.install-update')
    installDropdowns.forEach((idd)=>{
      idd.removeEventListener('click',eventClickDropdownUpdate)
      idd.addEventListener('click', eventClickDropdownUpdate)
    })

    $("#update-app-notice").show()
    $("#done-update-button").hide()

    $("#yes-update").show()
    $("#no-update").show()
    $("#update-processing-label").empty()
    $("#update-notices").empty()
    $("#update-app-modal").modal({ backdrop: "static", keyboard: false, })
    $("#update-app-modal").modal("show")
  }
}

function initMainTables() {
  $("#installedAppsTable").bootstrapTable("destroy")

  $("#installedAppsTable").bootstrapTable({ data: installedApps })
  $("#installedProxyAppsTable").bootstrapTable({ data: proxyApps })
  $("#mainAppsTable").bootstrapTable("destroy")
  $("#mainAppsTable").bootstrapTable({ data: availableApps })
  $("#incompatibleAppsTable").bootstrapTable("destroy")

  $("#incompatibleAppsTable").bootstrapTable({ data: incompatibleApps })
  $("#incompatibleAppsTable").find(".install>button").removeClass("btn-info btn-outline-secondary")
  $("#incompatibleAppsTable").find(".install>button").addClass("incompatible-app btn-danger")
  $(".main-app-list").removeClass("hidden")
  $(".installed-app-list").removeClass("hidden")
  create_destroy_events_table()

  $('#incompatibleAppsTable').on('post-body.bs.table', function (data) {
      create_destroy_events_table();
  
  })
}

function create_destroy_events_table(){
  let dropdowns = document.querySelectorAll('.dropdown-toggle')
  dropdowns.forEach((dd)=>{
      dd.removeEventListener('click',eventClickDropdown)
      dd.addEventListener('click', eventClickDropdown)
  })
}

function eventClickDropdown(e) {
  var el = this.nextElementSibling
  if (!el.classList.contains("header_dropdown")) {
    el.style.display = el.style.display==='block'?'none':'block'
  }
}

function eventClickDropdownUpdate(e) {
  let app_channel_label_version = e.target.id
  let app_channel_label_version_list = app_channel_label_version.split("_")
  chooseVersion(app_channel_label_version_list[3], app_channel_label_version_list[0],app_channel_label_version_list[1],app_channel_label_version_list[2],'update-app-notice')
  // app_channel_label_version

}
