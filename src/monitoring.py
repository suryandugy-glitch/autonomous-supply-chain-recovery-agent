"""
Monitoring Module for the Autonomous Supply Chain Recovery Agent
Continuously polls inventory/shipment APIs or simulators to retrieve current logistics state
and detect anomalies and constraint violations
"""

import time
import threading
import requests
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta
from .config import config
from .state_manager import state_manager
from .utils import setup_logging, safe_request

# Setup logger
logger = setup_logging(__name__)

class MonitoringModule:
    """Monitors the logistics environment for changes and disruptions"""

    def __init__(self, update_callback: Optional[Callable] = None):
        self.update_callback = update_callback
        self._monitoring_thread = None
        self._stop_monitoring = threading.Event()
        self._last_inventory_update = {}
        self._last_shipment_update = {}
        self._last_vendor_update = {}
        self._last_demand_update = {}

        # Monitoring intervals from config
        self.inventory_interval = config.get_agent_param('monitoring_interval') or 30
        self.shipment_interval = config.get_agent_param('monitoring_interval') or 30
        self.vendor_interval = config.get_agent_param('monitoring_interval') or 60
        self.demand_interval = config.get_agent_param('monitoring_interval') or 60

        # Endpoints from config
        self.endpoints = {
            'inventory': config.get_tool_endpoint('inventory_api'),
            'shipment': config.get_tool_endpoint('shipment_api'),
            'vendor': config.get_tool_endpoint('vendor_api'),
            'demand': config.get_tool_endpoint('demand_api')
        }

    def start_monitoring(self) -> None:
        """Start the monitoring thread"""
        if self._monitoring_thread is not None and self._monitoring_thread.is_alive():
            logger.warning("Monitoring is already running")
            return

        logger.info("Starting supply chain monitoring...")
        self._stop_monitoring.clear()
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()

    def stop_monitoring(self) -> None:
        """Stop the monitoring thread"""
        logger.info("Stopping supply chain monitoring...")
        self._stop_monitoring.set()
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=5.0)

    def _monitoring_loop(self) -> None:
        """Main monitoring loop"""
        logger.info("Monitoring loop started")

        # Track last update times for each data type
        last_inventory_check = 0
        last_shipment_check = 0
        last_vendor_check = 0
        last_demand_check = 0

        while not self._stop_monitoring.is_set():
            current_time = time.time()

            # Check inventory data
            if current_time - last_inventory_check >= self.inventory_interval:
                self._update_inventory_data()
                last_inventory_check = current_time

            # Check shipment data
            if current_time - last_shipment_check >= self.shipment_interval:
                self._update_shipment_data()
                last_shipment_check = current_time

            # Check vendor data
            if current_time - last_vendor_check >= self.vendor_interval:
                self._update_vendor_data()
                last_vendor_check = current_time

            # Check demand data
            if current_time - last_demand_check >= self.demand_interval:
                self._update_demand_data()
                last_demand_check = current_time

            # Sleep for a short interval to prevent busy waiting
            time.sleep(min(5, self.inventory_interval, self.shipment_interval,
                          self.vendor_interval, self.demand_interval))

        logger.info("Monitoring loop stopped")

    def _update_inventory_data(self) -> None:
        """Update inventory data from the inventory API"""
        try:
            logger.debug("Fetching inventory data...")
            response = safe_request('GET', self.endpoints['inventory'], timeout=10)

            if response and response.status_code == 200:
                inventory_data = response.json()
                self._process_inventory_updates(inventory_data)
                logger.debug(f"Updated inventory data for {len(inventory_data)} items")
            else:
                logger.warning(f"Failed to fetch inventory data: {response.status_code if response else 'No response'}")

        except Exception as e:
            logger.error(f"Error updating inventory data: {e}")

    def _update_shipment_data(self) -> None:
        """Update shipment data from the shipment API"""
        try:
            logger.debug("Fetching shipment data...")
            response = safe_request('GET', self.endpoints['shipment'], timeout=10)

            if response and response.status_code == 200:
                shipment_data = response.json()
                self._process_shipment_updates(shipment_data)
                logger.debug(f"Updated shipment data for {len(shipment_data)} shipments")
            else:
                logger.warning(f"Failed to fetch shipment data: {response.status_code if response else 'No response'}")

        except Exception as e:
            logger.error(f"Error updating shipment data: {e}")

    def _update_vendor_data(self) -> None:
        """Update vendor data from the vendor API"""
        try:
            logger.debug("Fetching vendor data...")
            response = safe_request('GET', self.endpoints['vendor'], timeout=10)

            if response and response.status_code == 200:
                vendor_data = response.json()
                self._process_vendor_updates(vendor_data)
                logger.debug(f"Updated vendor data for {len(vendor_data)} vendors")
            else:
                logger.warning(f"Failed to fetch vendor data: {response.status_code if response else 'No response'}")

        except Exception as e:
            logger.error(f"Error updating vendor data: {e}")

    def _update_demand_data(self) -> None:
        """Update demand forecast data from the demand API"""
        try:
            logger.debug("Fetching demand data...")
            response = safe_request('GET', self.endpoints['demand'], timeout=10)

            if response and response.status_code == 200:
                demand_data = response.json()
                self._process_demand_updates(demand_data)
                logger.debug(f"Updated demand data for {len(demand_data)} products")
            else:
                logger.warning(f"Failed to fetch demand data: {response.status_code if response else 'No response'}")

        except Exception as e:
            logger.error(f"Error updating demand data: {e}")

    def _process_inventory_updates(self, inventory_data: List[Dict[str, Any]]) -> None:
        """Process and store inventory updates"""
        try:
            for item in inventory_data:
                # Extract product ID - adjust based on actual API response format
                product_id = item.get('product_id') or item.get('id') or item.get('sku')
                if not product_id:
                    logger.warning("Inventory item missing product ID, skipping")
                    continue

                # Prepare inventory data for state manager
                processed_data = {
                    'quantity': item.get('quantity', 0),
                    'location': item.get('location', 'unknown'),
                    'available_quantity': item.get('available_quantity', item.get('quantity', 0)),
                    'reserved_quantity': item.get('reserved_quantity', 0),
                    'unit_cost': item.get('unit_cost', 0.0),
                    'last_restock': item.get('last_restock'),
                    'expiry_date': item.get('expiry_date')
                }

                # Update state manager
                state_manager.update_inventory(product_id, processed_data)

                # Check for significant changes that might indicate disruption
                self._check_inventory_disruptions(product_id, processed_data)

            # Notify callback if provided
            if self.update_callback:
                self.update_callback('inventory_update', {'count': len(inventory_data)})

        except Exception as e:
            logger.error(f"Error processing inventory updates: {e}")

    def _process_shipment_updates(self, shipment_data: List[Dict[str, Any]]) -> None:
        """Process and store shipment updates"""
        try:
            for shipment in shipment_data:
                # Extract shipment ID
                shipment_id = shipment.get('shipment_id') or shipment.get('id') or shipment.get('tracking_number')
                if not shipment_id:
                    logger.warning("Shipment missing ID, skipping")
                    continue

                # Calculate delay if available
                delay_hours = 0.0
                eta = shipment.get('eta')
                scheduled_delivery = shipment.get('scheduled_delivery')
                actual_delivery = shipment.get('actual_delivery')

                if eta and scheduled_delivery:
                    try:
                        eta_time = datetime.fromisoformat(eta.replace('Z', '+00:00'))
                        scheduled_time = datetime.fromisoformat(scheduled_delivery.replace('Z', '+00:00'))
                        delay_hours = max(0, (eta_time - scheduled_time).total_seconds() / 3600)
                    except:
                        pass
                elif actual_delivery and scheduled_delivery:
                    try:
                        actual_time = datetime.fromisoformat(actual_delivery.replace('Z', '+00:00'))
                        scheduled_time = datetime.fromisoformat(scheduled_delivery.replace('Z', '+00:00'))
                        delay_hours = max(0, (actual_time - scheduled_time).total_seconds() / 3600)
                    except:
                        pass

                # Prepare shipment data for state manager
                processed_data = {
                    'origin': shipment.get('origin', 'unknown'),
                    'destination': shipment.get('destination', 'unknown'),
                    'status': shipment.get('status', 'unknown'),
                    'eta': eta,
                    'scheduled_delivery': scheduled_delivery,
                    'actual_delivery': actual_delivery,
                    'delay_hours': delay_hours,
                    'weight_kg': shipment.get('weight_kg', 0.0),
                    'volume_m3': shipment.get('volume_m3', 0.0),
                    'contents': shipment.get('contents', []),
                    'carrier': shipment.get('carrier', 'unknown'),
                    'tracking_number': shipment.get('tracking_number', '')
                }

                # Update state manager
                state_manager.update_shipment(shipment_id, processed_data)

                # Check for significant changes that might indicate disruption
                self._check_shipment_disruptions(shipment_id, processed_data)

            # Notify callback if provided
            if self.update_callback:
                self.update_callback('shipment_update', {'count': len(shipment_data)})

        except Exception as e:
            logger.error(f"Error processing shipment updates: {e}")

    def _process_vendor_updates(self, vendor_data: List[Dict[str, Any]]) -> None:
        """Process and store vendor updates"""
        try:
            for vendor in vendor_data:
                # Extract vendor ID
                vendor_id = vendor.get('vendor_id') or vendor.get('id') or vendor.get('code')
                if not vendor_id:
                    logger.warning("Vendor missing ID, skipping")
                    continue

                # Prepare vendor data for state manager
                processed_data = {
                    'name': vendor.get('name', 'unknown'),
                    'reliability_score': vendor.get('reliability_score', 1.0),
                    'lead_time_days': vendor.get('lead_time_days', 7),
                    'capacity_units_per_day': vendor.get('capacity_units_per_day', 100),
                    'on_time_delivery_rate': vendor.get('on_time_delivery_rate', 1.0),
                    'quality_score': vendor.get('quality_score', 1.0),
                    'cost_factor': vendor.get('cost_factor', 1.0),
                    'specialties': vendor.get('specialties', []),
                    'geographic_coverage': vendor.get('geographic_coverage', []),
                    'is_active': vendor.get('is_active', True)
                }

                # Update state manager
                state_manager.update_vendor(vendor_id, processed_data)

                # Check for significant changes that might indicate disruption
                self._check_vendor_disruptions(vendor_id, processed_data)

            # Notify callback if provided
            if self.update_callback:
                self.update_callback('vendor_update', {'count': len(vendor_data)})

        except Exception as e:
            logger.error(f"Error processing vendor updates: {e}")

    def _process_demand_updates(self, demand_data: List[Dict[str, Any]]) -> None:
        """Process and store demand forecast updates"""
        try:
            for item in demand_data:
                # Extract product ID
                product_id = item.get('product_id') or item.get('id') or item.get('sku')
                if not product_id:
                    logger.warning("Demand item missing product ID, skipping")
                    continue

                # Prepare demand data for state manager
                processed_data = {
                    'forecasted_demand': item.get('forecasted_demand', 0),
                    'confidence_level': item.get('confidence_level', 0.5),
                    'forecast_period_days': item.get('forecast_period_days', 30),
                    'seasonality_factor': item.get('seasonality_factor', 1.0),
                    'trend_factor': item.get('trend_factor', 1.0),
                    'external_factors': item.get('external_factors', []),
                    'forecast_timestamp': item.get('timestamp', datetime.now().isoformat())
                }

                # Update state manager
                state_manager.update_demand_forecast(product_id, processed_data)

                # Check for significant changes that might indicate disruption
                self._check_demand_disruptions(product_id, processed_data)

            # Notify callback if provided
            if self.update_callback:
                self.update_callback('demand_update', {'count': len(demand_data)})

        except Exception as e:
            logger.error(f"Error processing demand updates: {e}")

    def _check_inventory_disruptions(self, product_id: str, current_data: Dict[str, Any]) -> None:
        """Check for inventory-related disruptions"""
        try:
            # Get previous inventory state for comparison
            previous_data = self._last_inventory_update.get(product_id, {})
            if not previous_data:
                # First time seeing this product, store current state and return
                self._last_inventory_update[product_id] = current_data.copy()
                return

            # Check for stockout (quantity dropped to zero or below safety stock)
            current_quantity = current_data.get('quantity', 0)
            previous_quantity = previous_data.get('quantity', 0)
            safety_stock = 10  # Could be made configurable

            if current_quantity <= 0 and previous_quantity > 0:
                # Stockout occurred
                disruption_data = {
                    'type': 'stockout',
                    'product_id': product_id,
                    'severity': 'high',
                    'description': f'Product {product_id} has gone out of stock',
                    'current_quantity': current_quantity,
                    'previous_quantity': previous_quantity,
                    'impact': 'Unable to fulfill customer orders'
                }
                state_manager.record_disruption(disruption_data)
                logger.warning(f"Stockout detected for product {product_id}")

            elif current_quantity < safety_stock and previous_quantity >= safety_stock:
                # Dropped below safety stock
                disruption_data = {
                    'type': 'low_inventory',
                    'product_id': product_id,
                    'severity': 'medium',
                    'description': f'Product {product_id} inventory dropped below safety stock',
                    'current_quantity': current_quantity,
                    'safety_stock_threshold': safety_stock,
                    'impact': 'Risk of stockout if not replenished soon'
                }
                state_manager.record_disruption(disruption_data)
                logger.warning(f"Low inventory detected for product {product_id}: {current_quantity} < {safety_stock}")

            # Update last known state
            self._last_inventory_update[product_id] = current_data.copy()

        except Exception as e:
            logger.error(f"Error checking inventory disruptions for {product_id}: {e}")

    def _check_shipment_disruptions(self, shipment_id: str, current_data: Dict[str, Any]) -> None:
        """Check for shipment-related disruptions"""
        try:
            # Get previous shipment state for comparison
            previous_data = self._last_shipment_update.get(shipment_id, {})
            if not previous_data:
                # First time seeing this shipment, store current state and return
                self._last_shipment_update[shipment_id] = current_data.copy()
                return

            # Check for significant delays
            current_delay = current_data.get('delay_hours', 0)
            previous_delay = previous_data.get('delay_hours', 0)
            max_acceptable_delay = 24  # hours

            if current_delay > max_acceptable_delay and previous_delay <= max_acceptable_delay:
                # Shipment became significantly delayed
                disruption_data = {
                    'type': 'delivery_delay',
                    'shipment_id': shipment_id,
                    'severity': 'high' if current_delay > 48 else 'medium',
                    'description': f'Shipment {shipment_id} experiencing significant delay',
                    'current_delay_hours': current_delay,
                    'previous_delay_hours': previous_delay,
                    'max_acceptable_delay_hours': max_acceptable_delay,
                    'impact': 'Late delivery to customer or next facility'
                }
                state_manager.record_disruption(disruption_data)
                logger.warning(f"Delivery delay detected for shipment {shipment_id}: {current_delay} hours")

            # Check for shipment status problems
            current_status = current_data.get('status', '').lower()
            previous_status = previous_data.get('status', '').lower()
            problem_statuses = ['delayed', 'lost', 'damaged', 'customs_hold', 'exception']

            if any(status in current_status for status in problem_statuses) and \
               not any(status in previous_status for status in problem_statuses):
                # Shipment entered problematic status
                disruption_data = {
                    'type': 'shipment_issue',
                    'shipment_id': shipment_id,
                    'severity': 'high',
                    'description': f'Shipment {shipment_id} encountered problems: {current_status}',
                    'current_status': current_status,
                    'previous_status': previous_status,
                    'impact': 'Delivery may be delayed or compromised'
                }
                state_manager.record_disruption(disruption_data)
                logger.warning(f"Shipment issue detected for {shipment_id}: {current_status}")

            # Update last known state
            self._last_shipment_update[shipment_id] = current_data.copy()

        except Exception as e:
            logger.error(f"Error checking shipment disruptions for {shipment_id}: {e}")

    def _check_vendor_disruptions(self, vendor_id: str, current_data: Dict[str, Any]) -> None:
        """Check for vendor-related disruptions"""
        try:
            # Get previous vendor state for comparison
            previous_data = self._last_vendor_update.get(vendor_id, {})
            if not previous_data:
                # First time seeing this vendor, store current state and return
                self._last_vendor_update[vendor_id] = current_data.copy()
                return

            # Check for significant reliability degradation
            current_reliability = current_data.get('reliability_score', 1.0)
            previous_reliability = previous_data.get('reliability_score', 1.0)
            reliability_threshold = 0.7  # Below 70% reliability is concerning

            if current_reliability < reliability_threshold and previous_reliability >= reliability_threshold:
                # Vendor reliability degraded significantly
                disruption_data = {
                    'type': 'vendor_reliability_degraded',
                    'vendor_id': vendor_id,
                    'severity': 'medium',
                    'description': f'Vendor {vendor_id} reliability dropped below acceptable threshold',
                    'current_reliability': current_reliability,
                    'previous_reliability': previous_reliability,
                    'reliability_threshold': reliability_threshold,
                    'impact': 'Increased risk of delivery failures or quality issues'
                }
                state_manager.record_disruption(disruption_data)
                logger.warning(f"Vendor reliability degradation detected for {vendor_id}: {current_reliability}")

            # Check for vendor deactivation
            was_active = previous_data.get('is_active', True)
            is_active = current_data.get('is_active', True)
            if was_active and not is_active:
                disruption_data = {
                    'type': 'vendor_deactivated',
                    'vendor_id': vendor_id,
                    'severity': 'high',
                    'description': f'Vendor {vendor_id} has been deactivated',
                    'impact': 'Loss of supply capacity requiring immediate alternative sourcing'
                }
                state_manager.record_disruption(disruption_data)
                logger.warning(f"Vendor deactivation detected for {vendor_id}")

            # Update last known state
            self._last_vendor_update[vendor_id] = current_data.copy()

        except Exception as e:
            logger.error(f"Error checking vendor disruptions for {vendor_id}: {e}")

    def _check_demand_disruptions(self, product_id: str, current_data: Dict[str, Any]) -> None:
        """Check for demand-related disruptions"""
        try:
            # Get previous demand state for comparison
            previous_data = self._last_demand_update.get(product_id, {})
            if not previous_data:
                # First time seeing this product's demand, store current state and return
                self._last_demand_update[product_id] = current_data.copy()
                return

            # Check for significant demand spikes
            current_forecast = current_data.get('forecasted_demand', 0)
            previous_forecast = previous_data.get('forecasted_demand', 0)

            if previous_forecast > 0:
                demand_increase_ratio = current_forecast / previous_forecast
                # Consider it a spike if demand doubled or more
                if demand_increase_ratio >= 2.0 and current_forecast > previous_forecast + 10:
                    disruption_data = {
                        'type': 'demand_spike',
                        'product_id': product_id,
                        'severity': 'medium',
                        'description': f'Significant increase in demand forecast for product {product_id}',
                        'current_forecast': current_forecast,
                        'previous_forecast': previous_forecast,
                        'increase_ratio': demand_increase_ratio,
                        'impact': 'May require increased inventory or expedited replenishment'
                    }
                    state_manager.record_disruption(disruption_data)
                    logger.warning(f"Demand spike detected for product {product_id}: {previous_forecast} -> {current_forecast}")

            # Update last known state
            self._last_demand_update[product_id] = current_data.copy()

        except Exception as e:
            logger.error(f"Error checking demand disruptions for {product_id}: {e}")

    def get_current_state_summary(self) -> Dict[str, Any]:
        """Get a summary of the current monitored state"""
        return {
            'inventory_count': len(state_manager.get_inventory()),
            'shipment_count': len(state_manager.get_shipment()),
            'vendor_count': len(state_manager.get_vendor()),
            'demand_forecast_count': len(state_manager.get_demand_forecast()),
            'last_update': datetime.now().isoformat(),
            'monitoring_active': not self._stop_monitoring.is_set()
        }

# Global monitoring module instance
monitoring_module = MonitoringModule()