class LongPress extends Polymer.Element {

  ready() {
    super.ready();
    document.addEventListener('mousedown', (e) => this.mouseDown(e, false));
    document.addEventListener('touchstart', (e) => this.mouseDown(e, true));
    document.addEventListener('mouseup', (e) => this.mouseUp(e, false));
    document.addEventListener('touchend', (e) => this.mouseUp(e, true));
    document.addEventListener('click', (e) => this._reset());
  }

  setConfig(config) {
    this._config = config;
    let tag = config.child.type;
    if(tag.startsWith("custom:"))
      tag = tag.substr(7);
    else
      tag = `hui-${tag}-element`;

    this.enabled = true;
    this.timer = null;

    this.child = document.createElement(tag);
    this.child.setConfig(config.child);
    this.appendChild(this.child);

    this.cover = document.createElement('div');
    this.cover.setAttribute("style", "position: absolute; top: 0; left: 0; width: 100%; height: 100%; visibility: hidden;");
    this.appendChild(this.cover);
  }

  set hass(hass) {
    this._hass = hass;
    this.child.hass = hass;
    this.enabled = true;
    if(hass.moreInfoEntityId) {
      this.enabled = false;
      this._reset();
    }
  }

  _reset() {
    if(this.timer) {
      clearTimeout(this.timer);
      this.timer = null;
    }
    let dlg = document.querySelector('home-assistant').shadowRoot.querySelector('ha-more-info-dialog');
    if(dlg)
      dlg.removeAttribute('modal');
    this.cover.style.visibility = 'hidden';
  }

  mouseDown(ev, touch) {
    this._reset();

    if (!this.enabled) return;
    if(!touch && ev.button != 0) return;

    let br = this.getBoundingClientRect();
    let cx = (touch)? ev.touches[0].clientX : ev.clientX;
    let cy = (touch)? ev.touches[0].clientY : ev.clientY;
    if( cx < br.left || cx > br.right || cy < br.top || cy > br.bottom)
      return;

    this.timer = setTimeout((e) => this.onHold(), 300);
  }

  mouseUp(ev, touch) {
    if(!this.enabled) return;
    this._reset();
  }

  onHold() {
    if(this._config.navigation_path) {
      history.pushState(null, null, this._config.navigation_path);
      let ev = new Event('location-changed', {
        bubbles: true,
        cancelable: false,
        composed: true,
      });
      this.dispatchEvent(ev);
    } else if (this._config.service) {
      const [domain, service] = this._config.service.split('.', 2);
      this._hass.callService(domain, service, this._config.service_data);
      this.cover.style.visibility='visible';
    } else {
      // Only open more-info dialog for now
      let ev = new Event('hass-more-info', {
        bubbles: true,
        cancelable: false,
        composed: true,
      });
      const entityId = this._config.entity || this._config.child.entity;
      ev.detail = { entityId };
      this.dispatchEvent(ev);
      document.querySelector('home-assistant').shadowRoot.querySelector('ha-more-info-dialog').setAttribute('modal', true);
    }
  }
}

customElements.define('long-press', LongPress)
