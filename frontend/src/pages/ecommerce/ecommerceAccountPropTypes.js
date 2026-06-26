import PropTypes from "prop-types";

export const fieldErrorPropType = PropTypes.shape({
  field: PropTypes.string,
  message: PropTypes.string,
});

export const ecommerceStylesPropType = PropTypes.shape({
  accountCard: PropTypes.object,
  formInput: PropTypes.object,
  saveBtn: PropTypes.object,
});
