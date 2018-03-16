Highlight Build Errors
======================

A plugin for [Sublime Text 3](http://www.sublimetext.com/) that highlights the lines that caused errors in the build.

![Screen capture with the Monokai theme](http://i.imgur.com/nj4WGFF.png)

## Feature

* Does only one thing: highlights the erroneous lines after a build
* Highlights are visible in the mini-map
* Customizable display (fill, outline, underline, icon...)
* Works fine with [Better Build System](https://sublime.wbond.net/packages/Better%20Build%20System)

## Installation

Install this plugin with the [Sublime Text Package Manager](https://sublime.wbond.net/), then restart Sublime Text.

# Configuration

As many Sublime Text plugins, the configuration can be modified from the menu `Preferences / Package Settings / Hightlight Build Errors`.

Here is the content of the default settings file:

```javascript
{
  // the plugin tests each regex and stops at the first match
  // "scope" is a key in the .tmTheme file
  // "display" can be "fill", "outline", "solid_underline", "stippled_underline" or "squiggly_underline"
  "colors": [
   {
      "regex": "note",
      "icon": "Packages/Highlight Build Errors/information.png"
    },
    {
      "regex": "warning",
      "scope": "invalid",
      "display": "outline",
      "icon": "Packages/Highlight Build Errors/warning.png"
    },
    {
      // default color, when none of the above matches
      "scope": "invalid",
      "display": "fill",
      "icon": "Packages/Highlight Build Errors/error.png"
    }
  ]
}

```

## Usage

Build as usual (<kbd>Ctrl</kbd>+<kbd>B</kbd> or <kbd>Cmd</kbd>+<kbd>B</kbd>).

Erroneous words or lines will be highlighted in the source files.

## Contributors

* Matthew Twomey
* Marcin Tolysz
* Connor Clark
* [Michael Yoo](https://github.com/sekjun9878) <michael@yoo.id.au>
* Aurelien Grenotton
* @evandrocoan

## Credits

* [Icons from famfamfam.com](http://www.famfamfam.com/lab/icons/silk/)
